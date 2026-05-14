from pydantic import BaseModel,EmailStr , Field
from datetime import datetime
from typing import List, Annotated,Literal,Optional
import Database.Tables as Tables
from Database.database import engine, sessionlocal
from sqlalchemy.orm import Session
from sqlalchemy import inspect, text

from fastapi import APIRouter, Depends, HTTPException, status
from passlib.context import CryptContext
from jose import JWTError, jwt

from Database.Tables import User

Tables.Base.metadata.create_all(bind=engine)


def _ensure_column(connection, table_name: str, column_name: str, column_ddl: str) -> None:
    inspector = inspect(connection)
    if table_name not in inspector.get_table_names():
        return

    existing_columns = {column["name"] for column in inspector.get_columns(table_name)}
    if column_name in existing_columns:
        return

    connection.execute(text(f'ALTER TABLE "{table_name}" ADD COLUMN {column_ddl}'))


def _sync_table_sequence(connection, table_name: str, pk_column: str = "id") -> None:
    sequence_name = connection.execute(
        text("SELECT pg_get_serial_sequence(:table_name, :pk_column)"),
        {"table_name": table_name, "pk_column": pk_column},
    ).scalar()

    if not sequence_name:
        return

    max_id = connection.execute(text(f'SELECT COALESCE(MAX("{pk_column}"), 0) FROM "{table_name}"')).scalar() or 0
    next_id = int(max_id) + 1
    connection.execute(text("SELECT setval(:sequence_name, :next_id, false)"), {"sequence_name": sequence_name, "next_id": next_id})


def _ensure_schema_extensions() -> None:
    with engine.begin() as connection:
        _ensure_column(connection, "users", "company_name", "company_name VARCHAR(255)")
        _ensure_column(connection, "users", "company_website", "company_website VARCHAR(255)")
        _ensure_column(connection, "jobs", "recruiter_id", "recruiter_id INTEGER")
        _ensure_column(connection, "jobs", "application_status", "application_status VARCHAR(20) DEFAULT 'open'")
        _ensure_column(connection, "apply_runs", "job_id", "job_id INTEGER")
        _ensure_column(connection, "applied_jobs", "job_id", "job_id INTEGER")
        connection.execute(text("UPDATE jobs SET application_status = 'open' WHERE application_status IS NULL"))
        _sync_table_sequence(connection, "users")
        _sync_table_sequence(connection, "jobs")
        _sync_table_sequence(connection, "favorite_jobs", "job_id")
        _sync_table_sequence(connection, "conversations")
        _sync_table_sequence(connection, "messages")
        _sync_table_sequence(connection, "jobs_shown")
        _sync_table_sequence(connection, "user_profile_pictures")
        _sync_table_sequence(connection, "user_resumes")
        _sync_table_sequence(connection, "mustaqbil_credentials")
        _sync_table_sequence(connection, "apply_runs")
        _sync_table_sequence(connection, "applied_jobs")


def sync_table_sequence(table_name: str, pk_column: str = "id") -> None:
    with engine.begin() as connection:
        _sync_table_sequence(connection, table_name, pk_column)


_ensure_schema_extensions()

def get_db():
    db = sessionlocal()
    try:
        yield db
    finally:
        db.close()


db_dependency = Annotated[Session, Depends(get_db)]