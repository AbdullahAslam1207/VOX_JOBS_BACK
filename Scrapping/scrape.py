from fastapi import APIRouter, Depends, HTTPException, status
from Database.Database_connection import db_dependency
from Database.Tables import Job
import json
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from Database.database import sessionlocal
from Scrapping.models import JobAdd
from sqlalchemy import select, func
from Scrapping.Scrappers.fetch_mustaqbil_jobs import fetch_jobs
# Router definition
router = APIRouter(
    prefix="/Scraper",
    tags=["scraper"],
)


async def insert_jobs_from_json(json_path: str):
    """Insert job data from JSON file into DB using an active session"""
    db = sessionlocal()  # ✅ create a real SQLAlchemy session

    with open(json_path, "r", encoding="utf-8") as f:
        jobs = json.load(f)

    inserted = 0
    skipped = 0
    # 🧹 1️⃣ Delete all existing jobs
    deleted_count = db.query(Job).delete()
    db.commit()
    print(f"🧹 Cleared {deleted_count} old jobs from database.")


    # ✅ use real query on ORM model
    current_max_id = db.query(func.max(Job.id)).scalar() or 0
    next_id = current_max_id + 1

    for job in jobs:
        try:
            job_data = JobAdd(**job)  # validate with Pydantic
            new_job = Job(id=next_id, **job_data.model_dump(exclude={"id"}))
            db.add(new_job)
            db.commit()
            next_id += 1
            inserted += 1
        except Exception as e:
            db.rollback()
            skipped += 1
            print(f"⚠️ Skipped job ({job.get('title')}): {e}")

    db.close()
    print(f"✅ Inserted {inserted} jobs (skipped {skipped})")


@router.get("/start_scraper", status_code=status.HTTP_200_OK)
async def start_scraper():
    import subprocess

    def run_node_scraper():
        print("🚀 Running Puppeteer scraper (JavaScript)...")
        subprocess.run(["node", "Scrapping/Scrappers/rozee.pk_new_scrapper.js"], capture_output=True, text=True)
        

    async def run_other_python_scrapers():
        result = await fetch_jobs()
        print("🐍 Running other Python scrapers...")
        subprocess.run(["python", "Scrapping/Scrappers/fetch_jobz_jobs.py"])
        # subprocess.run(["python", "Scrapping/Scrappers/fetch_mustaqbil_jobs.py"])
        
    def clean():
        print("=== Cleaning Data ===")
        subprocess.run(["python", "Scrapping/Scrappers/Cleaner.py"])
        print("✅ Data cleaning finished!")
        

    print("=== Starting All Scrapers ===")
    #run_node_scraper()
    await run_other_python_scrapers()
    clean()
    await insert_jobs_from_json("Scrapping/Scrappers/Data/final_jobs.json")
    print("✅ All scrapers finished!")
    return {status.HTTP_200_OK: "Scraping and cleaning completed successfully."}