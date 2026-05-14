from __future__ import annotations

from datetime import datetime
from typing import Any

from fastapi import APIRouter, Body, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy import func, or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from Auth_service.models import ALGORITHM, SECRET_KEY, bcrypt_context, create_access_token, validate_password_strength
from Database.Database_connection import db_dependency, sync_table_sequence
from Database.Tables import AppliedJob, Job, User, UserResume
from Recruiter_service.models import (
    JobSchemaFieldResponse,
    RecruiterApplicantResponse,
    RecruiterAuthResponse,
    RecruiterLoginRequest,
    RecruiterSignupRequest,
)

router = APIRouter(prefix="/api", tags=["recruiter"])
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/recruiter/login")

JOB_INTERNAL_FIELDS = {"id", "recruiter_id", "application_status"}
JOB_REQUIRED_FIELDS = {"title", "job_description"}


def _humanize_field_name(name: str) -> str:
    if name == "job_description":
        return "Description"
    return name.replace("_", " ").title()


def _field_type_for_column(name: str, column_type: Any) -> str:
    if name in {"job_description", "skills"}:
        return "textarea"
    if name in {"is_active"}:
        return "checkbox"
    if name in {"posted_date", "apply_before"}:
        return "text"
    if column_type.__class__.__name__.lower().startswith("integer"):
        return "number"
    return "text"


def _current_recruiter(db: Session, token: str) -> User:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token") from exc

    user_id = payload.get("id")
    email = payload.get("sub")
    user = None
    if user_id is not None:
        user = db.query(User).filter(User.id == int(user_id)).first()
    if not user and email:
        user = db.query(User).filter(User.email == email).first()

    if not user or user.role != "recruiter":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Recruiter access required")

    return user


def get_current_recruiter(db: db_dependency, token: str = Depends(oauth2_scheme)) -> User:
    return _current_recruiter(db, token)


def _serialize_job(job: Job, applicants_count: int = 0) -> dict[str, Any]:
    return {
        "id": job.id,
        "title": job.title,
        "company_name": job.company_name,
        "company_link": job.company_link,
        "job_link": job.job_link,
        "location": job.location,
        "city": job.city,
        "source_city": job.source_city,
        "salary": job.salary,
        "job_type": job.job_type,
        "job_shift": job.job_shift,
        "experience": job.experience,
        "education": job.education,
        "posted_date": job.posted_date,
        "apply_before": job.apply_before,
        "job_description": job.job_description,
        "skills": job.skills,
        "job_source": job.job_source,
        "is_active": bool(job.is_active),
        "recruiter_id": job.recruiter_id,
        "application_status": job.application_status or "open",
        "applicants_count": applicants_count,
    }


def _build_job_schema() -> list[JobSchemaFieldResponse]:
    schema: list[JobSchemaFieldResponse] = []
    for column in Job.__table__.columns:
        if column.name in JOB_INTERNAL_FIELDS:
            continue

        max_length = getattr(column.type, "length", None)
        schema.append(
            JobSchemaFieldResponse(
                name=column.name,
                label=_humanize_field_name(column.name),
                field_type=_field_type_for_column(column.name, column.type),
                required=column.name in JOB_REQUIRED_FIELDS,
                max_length=max_length,
                default="open" if column.name == "application_status" else None,
            )
        )

    return schema


def _normalize_job_payload(payload: dict[str, Any]) -> dict[str, Any]:
    data = dict(payload)
    if "description" in data and "job_description" not in data:
        data["job_description"] = data.pop("description")

    title = str(data.get("title", "")).strip()
    description = str(data.get("job_description", "")).strip()
    if not title:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="title is required")
    if not description:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="description is required")

    create_data: dict[str, Any] = {}
    for column in Job.__table__.columns:
        if column.name in JOB_INTERNAL_FIELDS:
            continue
        if column.name not in data:
            continue
        value = data[column.name]
        if isinstance(value, str):
            value = value.strip()
            if value == "":
                value = None
        create_data[column.name] = value

    create_data["title"] = title
    create_data["job_description"] = description
    create_data["application_status"] = "open"
    return create_data


def _job_applicant_count(db: Session, job: Job) -> int:
    application_filters = [AppliedJob.job_id == job.id]
    if job.job_link:
        application_filters.append(AppliedJob.job_url == job.job_link)
    return int(db.query(func.count(AppliedJob.id)).filter(or_(*application_filters)).scalar() or 0)


@router.post("/recruiter/signup", response_model=RecruiterAuthResponse, status_code=status.HTTP_201_CREATED)
async def recruiter_signup(payload: RecruiterSignupRequest, db: db_dependency):
    email = payload.email.strip().lower()
    existing_user = db.query(User).filter(User.email == email).first()
    if existing_user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email is already registered")

    validate_password_strength(payload.password)
    recruiter = User(
        fullname=payload.name.strip(),
        email=email,
        hashed_password=bcrypt_context.hash(payload.password),
        role="recruiter",
        is_active=True,
        company_name=payload.company_name.strip(),
        company_website=payload.company_website.strip() if payload.company_website else None,
    )
    db.add(recruiter)
    db.commit()
    db.refresh(recruiter)

    token = create_access_token(email=recruiter.email, user_id=recruiter.id)
    return RecruiterAuthResponse(
        access_token=token,
        id=recruiter.id,
        name=recruiter.fullname,
        email=recruiter.email,
        company_name=recruiter.company_name,
        company_website=recruiter.company_website,
    )


@router.post("/recruiter/login", response_model=RecruiterAuthResponse)
async def recruiter_login(payload: RecruiterLoginRequest, db: db_dependency):
    recruiter = db.query(User).filter(User.email == payload.email.strip().lower(), User.role == "recruiter").first()
    if not recruiter or not bcrypt_context.verify(payload.password, recruiter.hashed_password):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Incorrect email or password")

    token = create_access_token(email=recruiter.email, user_id=recruiter.id)
    return RecruiterAuthResponse(
        access_token=token,
        id=recruiter.id,
        name=recruiter.fullname,
        email=recruiter.email,
        company_name=recruiter.company_name,
        company_website=recruiter.company_website,
    )


@router.get("/recruiter/job-schema", response_model=list[JobSchemaFieldResponse])
async def recruiter_job_schema(_: User = Depends(get_current_recruiter)):
    return _build_job_schema()


@router.get("/recruiter/jobs")
async def recruiter_jobs(db: db_dependency, current_user: User = Depends(get_current_recruiter)):
    jobs = db.query(Job).filter(Job.recruiter_id == current_user.id).order_by(Job.id.desc()).all()
    serialized_jobs: list[dict[str, Any]] = []

    for job in jobs:
        serialized_jobs.append(_serialize_job(job, _job_applicant_count(db, job)))

    return {
        "jobs": serialized_jobs,
        "open_jobs": [job for job in serialized_jobs if job["application_status"] == "open"],
        "closed_jobs": [job for job in serialized_jobs if job["application_status"] == "closed"],
    }


@router.post("/jobs/create")
async def create_job(
    db: db_dependency,
    payload: dict[str, Any] = Body(...),
    current_user: User = Depends(get_current_recruiter),
):
    job_data = _normalize_job_payload(payload)
    job_data["recruiter_id"] = current_user.id

    new_job = Job(**job_data)
    db.add(new_job)

    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        if "jobs_pkey" not in str(exc.orig):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unable to create job") from exc

        # Repair a stale sequence and retry once.
        sync_table_sequence("jobs")
        retry_job = Job(**job_data)
        db.add(retry_job)
        try:
            db.commit()
            new_job = retry_job
        except IntegrityError as retry_exc:
            db.rollback()
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Job ID conflict, please retry") from retry_exc

    db.refresh(new_job)
    return _serialize_job(new_job, 0)


@router.patch("/jobs/{job_id}")
async def update_job(
    job_id: int,
    db: db_dependency,
    payload: dict[str, Any] = Body(...),
    current_user: User = Depends(get_current_recruiter),
):
    job = db.query(Job).filter(Job.id == job_id, Job.recruiter_id == current_user.id).first()
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

    data = dict(payload)
    if "description" in data and "job_description" not in data:
        data["job_description"] = data.pop("description")

    merged: dict[str, Any] = {}
    for column in Job.__table__.columns:
        if column.name in JOB_INTERNAL_FIELDS:
            continue
        merged[column.name] = data.get(column.name, getattr(job, column.name))

    updated_job = _normalize_job_payload(merged)
    updated_job["recruiter_id"] = current_user.id

    for key, value in updated_job.items():
        setattr(job, key, value)

    db.commit()
    db.refresh(job)
    return _serialize_job(job, _job_applicant_count(db, job))


@router.patch("/jobs/{job_id}/close")
async def close_job(
    job_id: int,
    db: db_dependency,
    current_user: User = Depends(get_current_recruiter),
):
    job = db.query(Job).filter(Job.id == job_id, Job.recruiter_id == current_user.id).first()
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

    job.application_status = "closed"
    db.commit()
    db.refresh(job)
    return _serialize_job(job, _job_applicant_count(db, job))


@router.delete("/jobs/{job_id}")
async def delete_job(
    job_id: int,
    db: db_dependency,
    current_user: User = Depends(get_current_recruiter),
):
    job = db.query(Job).filter(Job.id == job_id, Job.recruiter_id == current_user.id).first()
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

    db.query(AppliedJob).filter(AppliedJob.job_id == job.id).update({AppliedJob.job_id: None})
    db.delete(job)
    db.commit()

    return {"message": "Job deleted successfully"}


@router.get("/jobs/{job_id}/applicants", response_model=list[RecruiterApplicantResponse])
async def job_applicants(
    job_id: int,
    db: db_dependency,
    current_user: User = Depends(get_current_recruiter),
):
    job = db.query(Job).filter(Job.id == job_id, Job.recruiter_id == current_user.id).first()
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

    application_filters = [AppliedJob.job_id == job_id]
    if job.job_link:
        application_filters.append(AppliedJob.job_url == job.job_link)

    applications = (
        db.query(AppliedJob)
        .filter(or_(*application_filters))
        .order_by(AppliedJob.applied_at.desc().nullslast(), AppliedJob.created_at.desc())
        .all()
    )

    results: list[RecruiterApplicantResponse] = []
    for application in applications:
        resume = db.query(UserResume).filter(UserResume.user_id == application.user_id).first()
        applicant_name = application.user.fullname if application.user else application.email
        results.append(
            RecruiterApplicantResponse(
                name=applicant_name,
                email=application.email,
                resume_file_name=resume.file_name if resume else None,
                resume_download_url=(f"/apply/resume/{application.email}/download" if resume else None),
                applied_at=application.applied_at or application.created_at,
                status=application.status,
                site=application.site,
            )
        )

    return results