import base64
import hashlib
import os
import re
import subprocess
import tempfile
from datetime import datetime
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from cryptography.fernet import Fernet
from fastapi import APIRouter, BackgroundTasks, File, Form, HTTPException, Query, UploadFile
from sqlalchemy.exc import IntegrityError
from fastapi.responses import Response

from Apply_Now.models import (
    AppliedJobListResponse,
    AppliedJobResponse,
    ApplyRunCreateResponse,
    ApplyRunRequest,
    ApplyRunStatusResponse,
    MustaqbilCredentialRequest,
    MustaqbilCredentialResponse,
    ProfilePictureMetadataResponse,
    ProfilePictureUploadResponse,
    PlatformApplyRequest,
    PlatformApplyResponse,
    ResumeMetadataResponse,
    ResumeUploadResponse,
)
from Database.Database_connection import db_dependency
from Database.Tables import AppliedJob, ApplyRun, Job, MustaqbilCredential, User, UserProfilePicture, UserResume
from Database.database import sessionlocal

router = APIRouter(prefix="/apply", tags=["apply"])

SCRIPT_BY_SITE = {
    "mustakbil": "Mustaqbil_apply.js",
    "rozee": "Rozee_apply.js",
}
ALLOWED_RESUME_EXTENSIONS = {".pdf", ".doc", ".docx"}
ALLOWED_CONTENT_TYPES = {
    "application/pdf",
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}
ALLOWED_IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}
ALLOWED_IMAGE_CONTENT_TYPES = {
    "image/png",
    "image/jpeg",
    "image/webp",
}
MAX_RESUME_SIZE_BYTES = 5 * 1024 * 1024
MAX_IMAGE_SIZE_BYTES = 3 * 1024 * 1024
APPLY_TIMEOUT_SECONDS = 600
ROZEE_APPLY_URL_TEMPLATE = (
    "https://apply.rozeegpt.ai/{job_id}?currency=PKR"
    "&utm_source=rozeeweb&utm_medium=website&utm_campaign=rozeeweb&utm_suggested=Y"
)


def _resolve_site(url: str) -> str:
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower()
    if "mustakbil.com" in host:
        return "mustakbil"
    if "rozee.pk" in host:
        return "rozee"
    raise HTTPException(status_code=400, detail="Unsupported URL domain. Only mustakbil.com and rozee.pk are supported")


def _extract_rozee_job_id(url: str) -> str:
    parsed = urlparse(url)
    path = parsed.path or ""
    query_params = parse_qs(parsed.query or "")

    # Common pattern: /seeker/<slug>--127508
    match = re.search(r"--(\d+)(?:/)?$", path)
    if match:
        return match.group(1)

    # Common query pattern: utm_content=job_127508
    utm_content = (query_params.get("utm_content") or [""])[0]
    match = re.search(r"job_(\d+)", utm_content)
    if match:
        return match.group(1)

    # Fallback to explicit id/job_id in query params
    for key in ("id", "job_id"):
        value = (query_params.get(key) or [""])[0]
        if value.isdigit():
            return value

    # Final fallback: first long numeric token in the path
    match = re.search(r"(\d{4,})", path)
    if match:
        return match.group(1)

    raise ValueError("Unable to extract Rozee job id from URL")


def _build_rozee_apply_url(source_url: str) -> str:
    job_id = _extract_rozee_job_id(source_url)
    return ROZEE_APPLY_URL_TEMPLATE.format(job_id=job_id)


def _build_fernet() -> Fernet:
    raw = os.getenv("APPLY_CREDENTIALS_KEY", "change-me-apply-secret")
    digest = hashlib.sha256(raw.encode("utf-8")).digest()
    key = base64.urlsafe_b64encode(digest)
    return Fernet(key)


def _encrypt_password(password: str) -> str:
    return _build_fernet().encrypt(password.encode("utf-8")).decode("utf-8")


def _decrypt_password(password_encrypted: str) -> str:
    return _build_fernet().decrypt(password_encrypted.encode("utf-8")).decode("utf-8")


def _run_apply_job(run_id: int, script_name: str, url: str, job_title: str | None, company_name: str | None) -> None:
    db = sessionlocal()
    temp_resume_path = None
    try:
        run = db.query(ApplyRun).filter(ApplyRun.id == run_id).first()
        if not run:
            return

        run.status = "running"
        run.started_at = datetime.utcnow()
        db.commit()

        backend_root = Path(__file__).resolve().parents[1]
        script_path = backend_root / "Apply_Now" / script_name

        status = "success"
        stdout = ""
        stderr = ""
        error_message = None
        applied_at = None

        try:
            env = os.environ.copy()

            if run.site == "mustakbil":
                credential = db.query(MustaqbilCredential).filter(MustaqbilCredential.user_id == run.user_id).first()
                if not credential:
                    raise ValueError("Mustaqbil credentials not found for this user")

                env["MUSTAQBIL_EMAIL"] = credential.mustaqbil_email
                env["MUSTAQBIL_PASSWORD"] = _decrypt_password(credential.mustaqbil_password_encrypted)
                command = ["node", str(script_path), url]
            elif run.site == "rozee":
                resume = db.query(UserResume).filter(UserResume.user_id == run.user_id).first()
                if not resume:
                    raise ValueError("Resume not found for this user")

                rozee_apply_url = _build_rozee_apply_url(url)

                suffix = Path(resume.file_name or "resume.pdf").suffix or ".pdf"
                fd, temp_path = tempfile.mkstemp(prefix="rozee_resume_", suffix=suffix)
                os.close(fd)
                with open(temp_path, "wb") as temp_file:
                    temp_file.write(resume.file_data)

                temp_resume_path = temp_path
                env["ROZEE_RESUME_PATH"] = temp_resume_path
                command = ["node", str(script_path), rozee_apply_url]
            else:
                raise ValueError("Unsupported site for apply run")

            completed = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=APPLY_TIMEOUT_SECONDS,
                cwd=str(backend_root),
                env=env,
            )
            stdout = completed.stdout or ""
            stderr = completed.stderr or ""
            if completed.returncode != 0:
                status = "failed"
                error_message = (stderr or "Apply script exited with non-zero status")[:2000]
            else:
                applied_at = datetime.utcnow()
        except subprocess.TimeoutExpired:
            status = "timeout"
            error_message = "Apply script timed out"
            stderr = "Apply script timed out"
        except Exception as exc:
            status = "failed"
            error_message = str(exc)[:2000]
            stderr = str(exc)

        run.status = status
        run.stdout = stdout
        run.stderr = stderr
        run.finished_at = datetime.utcnow()

        applied_job = AppliedJob(
            user_id=run.user_id,
            job_id=run.job_id,
            email=run.email,
            site=run.site,
            job_url=run.url,
            job_title=job_title,
            company_name=company_name,
            status=status,
            run_id=run.id,
            error_message=error_message,
            applied_at=applied_at,
        )
        db.add(applied_job)
        db.commit()
    finally:
        if temp_resume_path and os.path.exists(temp_resume_path):
            try:
                os.remove(temp_resume_path)
            except OSError:
                pass
        db.close()


@router.post("/platform", response_model=PlatformApplyResponse, status_code=201)
async def apply_to_platform_job(payload: PlatformApplyRequest, db: db_dependency):
    user = db.query(User).filter(User.email == payload.email.strip().lower()).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    job = db.query(Job).filter(Job.id == payload.job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if not bool(job.is_active) or (job.application_status or "open") != "open":
        raise HTTPException(status_code=400, detail="This job is not open for applications")

    resume = db.query(UserResume).filter(UserResume.user_id == user.id).first()
    if not resume:
        raise HTTPException(status_code=400, detail="Upload your resume before applying")

    existing = (
        db.query(AppliedJob)
        .filter(AppliedJob.user_id == user.id, AppliedJob.job_id == job.id, AppliedJob.site == "platform")
        .first()
    )
    if existing:
        raise HTTPException(status_code=409, detail="You have already applied to this job")

    applied_job = AppliedJob(
        user_id=user.id,
        job_id=job.id,
        email=user.email,
        site="platform",
        job_url=job.job_link or f"platform-job-{job.id}",
        job_title=job.title,
        company_name=job.company_name,
        status="submitted",
        applied_at=datetime.utcnow(),
    )
    db.add(applied_job)

    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="You have already applied to this job") from exc

    db.refresh(applied_job)
    return PlatformApplyResponse(
        application_id=applied_job.id,
        status=applied_job.status,
        message="Application submitted successfully",
    )


@router.post("/run", response_model=ApplyRunCreateResponse)
async def start_apply_run(payload: ApplyRunRequest, background_tasks: BackgroundTasks, db: db_dependency):
    user = db.query(User).filter(User.email == payload.email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    site = _resolve_site(str(payload.url))
    script_name = SCRIPT_BY_SITE[site]

    # Fail early with 400 instead of queueing a run that will fail later.
    if site == "mustakbil":
        credential = db.query(MustaqbilCredential).filter(MustaqbilCredential.user_id == user.id).first()
        if not credential:
            raise HTTPException(
                status_code=400,
                detail="Mustaqbil credentials are required before running apply for mustakbil.com",
            )

    if site == "rozee":
        resume = db.query(UserResume).filter(UserResume.user_id == user.id).first()
        if not resume:
            raise HTTPException(
                status_code=400,
                detail="Resume is required before running apply for rozee.pk",
            )
        try:
            _extract_rozee_job_id(str(payload.url))
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail="Unable to extract Rozee job id from the provided URL",
            )

    run = ApplyRun(
        user_id=user.id,
        job_id=payload.job_id,
        email=user.email,
        url=str(payload.url),
        site=site,
        status="queued",
    )
    db.add(run)
    db.commit()
    db.refresh(run)

    background_tasks.add_task(
        _run_apply_job,
        run.id,
        script_name,
        str(payload.url),
        payload.job_title,
        payload.company_name,
    )

    return ApplyRunCreateResponse(run_id=run.id, status=run.status, site=site)


@router.get("/run/{run_id}", response_model=ApplyRunStatusResponse)
async def get_apply_run(run_id: int, db: db_dependency):
    run = db.query(ApplyRun).filter(ApplyRun.id == run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    return run


@router.get("/applied-jobs/{email}", response_model=AppliedJobListResponse)
async def get_applied_jobs(
    email: str,
    db: db_dependency,
    status: str | None = Query(default=None),
    site: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
):
    query = db.query(AppliedJob).filter(AppliedJob.email == email)
    if status:
        query = query.filter(AppliedJob.status == status)
    if site:
        query = query.filter(AppliedJob.site == site)

    total = query.count()
    jobs = (
        query.order_by(AppliedJob.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    return AppliedJobListResponse(jobs=[AppliedJobResponse.model_validate(job) for job in jobs], total=total)


@router.post("/resume", response_model=ResumeUploadResponse)
async def upload_resume(db: db_dependency, email: str = Form(...), file: UploadFile = File(...)):
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    extension = Path(file.filename or "").suffix.lower()
    if extension not in ALLOWED_RESUME_EXTENSIONS:
        raise HTTPException(status_code=400, detail="Only PDF, DOC, and DOCX files are allowed")

    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(status_code=400, detail="Invalid content type for resume upload")

    file_bytes = await file.read()
    if len(file_bytes) > MAX_RESUME_SIZE_BYTES:
        raise HTTPException(status_code=400, detail="File size exceeds 5MB")

    existing_resume = db.query(UserResume).filter(UserResume.user_id == user.id).first()
    if existing_resume:
        existing_resume.file_name = file.filename or "resume"
        existing_resume.content_type = file.content_type or "application/octet-stream"
        existing_resume.file_data = file_bytes
        existing_resume.email = user.email
        existing_resume.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(existing_resume)
        saved_resume = existing_resume
    else:
        saved_resume = UserResume(
            user_id=user.id,
            email=user.email,
            file_name=file.filename or "resume",
            content_type=file.content_type or "application/octet-stream",
            file_data=file_bytes,
        )
        db.add(saved_resume)
        db.commit()
        db.refresh(saved_resume)

    return ResumeUploadResponse(
        message="Resume uploaded successfully",
        email=user.email,
        file_name=saved_resume.file_name,
        content_type=saved_resume.content_type,
        uploaded_at=saved_resume.uploaded_at,
    )


@router.get("/resume/{email}", response_model=ResumeMetadataResponse)
async def get_resume_metadata(email: str, db: db_dependency):
    resume = db.query(UserResume).filter(UserResume.email == email).first()
    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found")

    return ResumeMetadataResponse(
        email=resume.email,
        file_name=resume.file_name,
        content_type=resume.content_type,
        file_size=len(resume.file_data or b""),
        uploaded_at=resume.uploaded_at,
        updated_at=resume.updated_at,
    )


@router.get("/resume/{email}/download")
async def download_resume(email: str, db: db_dependency):
    resume = db.query(UserResume).filter(UserResume.email == email).first()
    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found")

    return Response(
        content=resume.file_data,
        media_type=resume.content_type,
        headers={"Content-Disposition": f'attachment; filename="{resume.file_name}"'},
    )


@router.post("/profile-picture", response_model=ProfilePictureUploadResponse)
async def upload_profile_picture(db: db_dependency, email: str = Form(...), file: UploadFile = File(...)):
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    extension = Path(file.filename or "").suffix.lower()
    if extension not in ALLOWED_IMAGE_EXTENSIONS:
        raise HTTPException(status_code=400, detail="Only PNG, JPG, JPEG, and WEBP files are allowed")

    if file.content_type not in ALLOWED_IMAGE_CONTENT_TYPES:
        raise HTTPException(status_code=400, detail="Invalid content type for profile picture upload")

    image_bytes = await file.read()
    if len(image_bytes) > MAX_IMAGE_SIZE_BYTES:
        raise HTTPException(status_code=400, detail="Image size exceeds 3MB")

    existing = db.query(UserProfilePicture).filter(UserProfilePicture.user_id == user.id).first()
    if existing:
        existing.file_name = file.filename or "profile-picture"
        existing.content_type = file.content_type or "application/octet-stream"
        existing.image_data = image_bytes
        existing.email = user.email
        existing.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(existing)
        saved = existing
    else:
        saved = UserProfilePicture(
            user_id=user.id,
            email=user.email,
            file_name=file.filename or "profile-picture",
            content_type=file.content_type or "application/octet-stream",
            image_data=image_bytes,
        )
        db.add(saved)
        db.commit()
        db.refresh(saved)

    return ProfilePictureUploadResponse(
        message="Profile picture uploaded successfully",
        email=user.email,
        file_name=saved.file_name,
        content_type=saved.content_type,
        uploaded_at=saved.uploaded_at,
    )


@router.get("/profile-picture/{email}", response_model=ProfilePictureMetadataResponse)
async def get_profile_picture_metadata(email: str, db: db_dependency):
    profile_pic = db.query(UserProfilePicture).filter(UserProfilePicture.email == email).first()
    if not profile_pic:
        raise HTTPException(status_code=404, detail="Profile picture not found")

    return ProfilePictureMetadataResponse(
        email=profile_pic.email,
        file_name=profile_pic.file_name,
        content_type=profile_pic.content_type,
        file_size=len(profile_pic.image_data or b""),
        uploaded_at=profile_pic.uploaded_at,
        updated_at=profile_pic.updated_at,
    )


@router.get("/profile-picture/{email}/download")
async def download_profile_picture(email: str, db: db_dependency):
    profile_pic = db.query(UserProfilePicture).filter(UserProfilePicture.email == email).first()
    if not profile_pic:
        raise HTTPException(status_code=404, detail="Profile picture not found")

    return Response(
        content=profile_pic.image_data,
        media_type=profile_pic.content_type,
        headers={"Content-Disposition": f'inline; filename="{profile_pic.file_name}"'},
    )


@router.post("/mustaqbil-credentials", response_model=MustaqbilCredentialResponse)
async def save_mustaqbil_credentials(payload: MustaqbilCredentialRequest, db: db_dependency):
    user = db.query(User).filter(User.email == payload.email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    encrypted_password = _encrypt_password(payload.mustaqbil_password)

    existing = db.query(MustaqbilCredential).filter(MustaqbilCredential.user_id == user.id).first()
    if existing:
        existing.email = user.email
        existing.mustaqbil_email = payload.mustaqbil_email
        existing.mustaqbil_password_encrypted = encrypted_password
        existing.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(existing)
        credential = existing
    else:
        credential = MustaqbilCredential(
            user_id=user.id,
            email=user.email,
            mustaqbil_email=payload.mustaqbil_email,
            mustaqbil_password_encrypted=encrypted_password,
        )
        db.add(credential)
        db.commit()
        db.refresh(credential)

    return MustaqbilCredentialResponse(
        email=credential.email,
        mustaqbil_email=credential.mustaqbil_email,
        mustaqbil_password=_decrypt_password(credential.mustaqbil_password_encrypted),
        created_at=credential.created_at,
        updated_at=credential.updated_at,
    )


@router.get("/mustaqbil-credentials/{email}", response_model=MustaqbilCredentialResponse)
async def get_mustaqbil_credentials(email: str, db: db_dependency):
    credential = db.query(MustaqbilCredential).filter(MustaqbilCredential.email == email).first()
    if not credential:
        raise HTTPException(status_code=404, detail="Mustaqbil credentials not found")

    return MustaqbilCredentialResponse(
        email=credential.email,
        mustaqbil_email=credential.mustaqbil_email,
        mustaqbil_password=_decrypt_password(credential.mustaqbil_password_encrypted),
        created_at=credential.created_at,
        updated_at=credential.updated_at,
    )
