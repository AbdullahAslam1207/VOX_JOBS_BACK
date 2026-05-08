from datetime import datetime, timedelta
from typing import Annotated,Literal
from fastapi import APIRouter, Depends, Query
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel ,EmailStr, Field, field_validator
from sqlalchemy.orm import Session
from passlib.context import CryptContext
from jose import JWTError, jwt
from Database.Database_connection import db_dependency
from Database.Tables import User
from Auth_service.models import create_access_token,CreateUserRequest,bcrypt_context,UserLoginRequest,Token ,validate_password_strength
from sqlalchemy import or_, and_
import re
from Database.Database_connection import db_dependency
from Database.Tables import Job, FavoriteJob
from CRUD.models import JobCreateRequest, JobList, FavoriteJobCreate, Delete_Favorite_Job ,FavoriteJobResponse

# Router definition
router = APIRouter(
    prefix="/CRUD",
    tags=["crud"],
)

@router.post("/add", status_code=status.HTTP_201_CREATED)
async def add_jobs(job_list: JobList,db: db_dependency):
    # Simple loop version — clear and easy to follow
    for job_data in job_list.jobs:
        job_dict = job_data.dict()  # Convert Pydantic object to Python dict
        new_job = Job(
            title=job_dict["title"],
            company_name=job_dict.get("company_name"),
            company_link=job_dict.get("company_link"),
            job_link=job_dict.get("job_link"),
            location=job_dict.get("location"),
            city=job_dict.get("city"),
            source_city=job_dict.get("source_city"),
            salary=job_dict.get("salary"),
            job_type=job_dict.get("job_type"),
            job_shift=job_dict.get("job_shift"),
            experience=job_dict.get("experience"),
            education=job_dict.get("education"),
            posted_date=job_dict.get("posted_date"),
            apply_before=job_dict.get("apply_before"),
            job_description=job_dict.get("job_description"),
            skills=job_dict.get("skills"),
            job_source=job_dict.get("job_source"),
            is_active=job_dict.get("is_active", True)
        )

        db.add(new_job)  # Add each job individually

    db.commit()
    return {"message": f"{len(job_list.jobs)} jobs successfully added."}
   
@router.get("/Get_jobs", response_model=list[JobCreateRequest])
async def get_jobs(
    db: db_dependency,
    query: str | None = None,
    location: str | None = None,
    city: str | None = None,
    only_remote: bool = False,
    limit: int | None = Query(default=None, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
):
    jobs_query = db.query(Job)

    if query:
        query_term = f"%{query.strip()}%"
        jobs_query = jobs_query.filter(
            or_(
                Job.title.ilike(query_term),
                Job.company_name.ilike(query_term),
                Job.location.ilike(query_term),
                Job.city.ilike(query_term),
                Job.job_description.ilike(query_term),
                Job.skills.ilike(query_term),
            )
        )

    if location:
        jobs_query = jobs_query.filter(Job.location.ilike(f"%{location.strip()}%"))

    if city:
        jobs_query = jobs_query.filter(Job.city.ilike(city.strip()))

    if only_remote:
        jobs_query = jobs_query.filter(Job.location.ilike("%remote%"))

    jobs_query = jobs_query.order_by(Job.id.desc())

    if limit is not None:
        jobs_query = jobs_query.offset(offset).limit(limit)

    jobs = jobs_query.all()
    return jobs

ALLOWED_CITIES = {"Lahore", "Karachi", "Islamabad", "Rawalpindi"}
VALID_CITIES = ["Lahore", "Karachi", "Islamabad", "Rawalpindi"]


@router.get("/get_jobs_by_city", response_model=list[JobCreateRequest])
async def get_jobs_by_city(
    city: str, db: db_dependency
):
    # Validate city
    if city not in ALLOWED_CITIES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid city '{city}'. Allowed cities: {', '.join(ALLOWED_CITIES)}"
        )

    # Fetch jobs from the allowed city
    jobs = db.query(Job).filter(Job.city == city).all()
    return jobs

@router.get("/get_jobs_by_title", response_model=list[JobCreateRequest])
async def get_jobs_by_title_and_city(query: str , db: db_dependency):
    # Normalize query
    query_lower = query.lower()

    # Extract city if mentioned in query
    city = None
    for c in VALID_CITIES:
        if c.lower() in query_lower:
            city = c
            query_lower = query_lower.replace(f"in {c.lower()}", "").strip()
            break

    # Remove extra words like "in" if not followed by city
    query_lower = re.sub(r"\bin\b", "", query_lower).strip()

    # Now, query_lower = job title portion
    title = query_lower.title()  # e.g. "Web Developer"

    # ---------------------- STEP 1: Exact match ----------------------
    filters = [Job.title.ilike(title)]
    if city:
        filters.append(Job.city.ilike(city))

    exact_matches = db.query(Job).filter(and_(*filters)).all()
    if exact_matches:
        return exact_matches

    # ---------------------- STEP 2: Partial match (title + city) ----------------------
    title_keywords = title.split()
    title_condition = or_(*[Job.title.ilike(f"%{word}%") for word in title_keywords])

    if city:
        partial_matches = db.query(Job).filter(and_(title_condition, Job.city.ilike(city))).all()
        if partial_matches:
            return partial_matches

    # ---------------------- STEP 3: Fallback — search by title only ----------------------
    fallback_matches = db.query(Job).filter(title_condition).all()
    return fallback_matches
@router.post("/favorite/add", status_code=201)
async def add_favorite_job(fav_job: FavoriteJobCreate, db: db_dependency):


    new_fav = FavoriteJob(
        user_id=fav_job.user_id,
        
        email=fav_job.email,
        title=fav_job.title,
        company_name=fav_job.company_name,
        company_link=fav_job.company_link,
        job_link=fav_job.job_link,
        location=fav_job.location,
        city=fav_job.city,
        source_city=fav_job.source_city,
        salary=fav_job.salary,
        job_type=fav_job.job_type,
        job_shift=fav_job.job_shift,
        experience=fav_job.experience,
        education=fav_job.education,
        posted_date=fav_job.posted_date,
        apply_before=fav_job.apply_before,
        job_description=fav_job.job_description,
        skills=fav_job.skills,
        job_source=fav_job.job_source,
        is_active=fav_job.is_active
    )

    db.add(new_fav)
    db.commit()
    db.refresh(new_fav)

    return {"message": "Job added to favorites", "favorite_id": new_fav.job_id}


@router.get("/favorite/{user_id}", response_model=list[FavoriteJobResponse])
async def get_favorite_jobs(user_id: int, db: db_dependency):
    fav_jobs = db.query(FavoriteJob).filter(FavoriteJob.user_id == user_id).all()
    return fav_jobs

@router.delete("/favorite/delete", status_code=200)
async def delete_favorite_job(payload: Delete_Favorite_Job, db: db_dependency):

    fav_job = db.query(FavoriteJob).filter(
        FavoriteJob.job_id == payload.fav_id,
        FavoriteJob.user_id == payload.user_id
    ).first()

    if not fav_job:
        raise HTTPException(status_code=404, detail="Favorite job not found or does not belong to user")

    db.delete(fav_job)
    db.commit()

    return {"message": "Favorite job deleted successfully"}
