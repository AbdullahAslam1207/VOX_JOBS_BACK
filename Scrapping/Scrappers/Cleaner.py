import json

# ------------------- JOBZ.PK CLEANER -------------------
def clean_jobz_data(jobz_data):
    cleaned = []
    for source_city, jobs in jobz_data.items():
        for job in jobs:
            details = job.get("details", {})
            cleaned.append({
                "title": job.get("title"),
                "company_name": details.get("Organization", {}).get("value", ""),
                "company_link": (details.get("Organization", {}).get("links") or [""])[0],
                "job_link": job.get("job_url"),
                "location": details.get("Vacancy Location", {}).get("value", ""),
                "city": details.get("Area / Town", {}).get("value", ""),
                "source_city": source_city,
                "salary": "",
                "job_type": details.get("Job Type", ""),
                "job_shift": "",
                "experience": "",
                "education": details.get("Education", {}).get("value", ""),
                "posted_date": details.get("Date Posted / Updated", ""),
                "apply_before": details.get("Expected Last Date", ""),
                "job_description": "",
                "skills": "",
                "job_source": "jobz.pk"
            })
    return cleaned


# ------------------- MUSTAKBIL CLEANER -------------------
def clean_mustakbil_data(mustakbil_data):
    cleaned = []
    for source_city, jobs in mustakbil_data.items():
        for job in jobs:
            cleaned.append({
                "title": job.get("title"),
                "company_name": job.get("company"),
                "company_link": "",
                "job_link": f"https://www.mustakbil.com/jobs/job/{job.get('id')}",
                "location": job.get("city", ""),
                "city": job.get("city", ""),
                "source_city": source_city,
                "salary": job.get("salary", ""),
                "job_type": job.get("type", ""),
                "job_shift": job.get("shift", ""),
                "experience": job.get("experienceLevel", ""),
                "education": "",
                "posted_date": job.get("postedOn", ""),
                "apply_before": "",
                "job_description": job.get("description", ""),
                "skills": "",
                "job_source": "mustakbil.com"
            })
    return cleaned


# ------------------- ROZEE.PK CLEANER -------------------
def clean_rozee_data(rozee_data, source_city=None):
    cleaned = []
    for job in rozee_data:
        cities = job.get("Job Location") or job.get("Location") or ""
        if isinstance(cities, list):
            city_value = ", ".join(cities)
        else:
            city_value = cities

        cleaned.append({
            "title": job.get("Job Title"),
            "company_name": job.get("Company Name"),
            "company_link": job.get("Company Link"),
            "job_link": job.get("Job Link"),
            "location": job.get("Job Location") or job.get("Location", ""),
            "city": city_value,
            "source_city": source_city or "",
            "salary": job.get("Salary", ""),
            "job_type": job.get("Job Type", ""),
            "job_shift": job.get("Job Shift", ""),
            "experience": job.get("Minimum Experience", ""),
            "education": job.get("Minimum Education", ""),
            "posted_date": job.get("Posting Date", ""),
            "apply_before": job.get("Apply Before", ""),
            "job_description": job.get("Job Description", ""),
            "skills": job.get("Skills Required", ""),
            "job_source": "rozee.pk"
        })
    return cleaned


import csv
import json

# ------------------- ROZEE.PK CLEANER (CSV VERSION) -------------------
def clean_rozee_csv(csv_path):
    cleaned = []

    with open(csv_path, newline='', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            cleaned.append({
                "title": row.get("Job Title", "").strip(),
                "company_name": row.get("Company Name", "").strip(),
                "company_link": row.get("Company Link", "").strip(),
                "job_link": row.get("Job Link", "").strip(),
                "location": row.get("Job Location", "").strip() or row.get("Location", "").strip(),
                "city": row.get("City", "").strip(),
                "source_city": row.get("City", "").strip(),
                "salary": row.get("Salary", "").strip(),
                "job_type": row.get("Job Type", "").strip(),
                "job_shift": row.get("Job Shift", "").strip(),
                "experience": row.get("Minimum Experience", "").strip(),
                "education": row.get("Minimum Education", "").strip(),
                "posted_date": row.get("Posting Date", "").strip(),
                "apply_before": row.get("Apply Before", "").strip(),
                "job_description": row.get("Job Description", "").strip(),
                "skills": row.get("Skills Required", "").strip(),
                "job_source": "rozee.pk"
            })

    print(f"✅ Cleaned {len(cleaned)} Rozee jobs from CSV.")
    return cleaned


# ------------------- MERGE FUNCTION -------------------
def merge_all_sources(jobz_data, mustakbil_data, rozee_citywise_data, output_path="Scrapping/Scrappers/Data/final_jobs.json"):
    all_jobs = []
    
    # Jobz.pk
    all_jobs.extend(clean_jobz_data(jobz_data))
    
    # Mustakbil
    all_jobs.extend(clean_mustakbil_data(mustakbil_data))
    
    # Rozee (assuming dict by city, like Lahore/Islamabad)
    rozee_cleaned_data = clean_rozee_csv(rozee_citywise_data)
    all_jobs.extend(rozee_cleaned_data)

    
    # Save unified data
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(all_jobs, f, indent=4, ensure_ascii=False)
    
    print(f"✅ Merged {len(all_jobs)} jobs saved to {output_path}")


    
if __name__ == "__main__":
    # ✅ Load JSON and CSV data before passing
    with open("Scrapping/Scrappers/Data/jobs_jobz.json", "r", encoding="utf-8") as f:
        jobz_data = json.load(f)

    with open("Scrapping/Scrappers/Data/jobs_data_mustaqbil.json", "r", encoding="utf-8") as f:
        mustakbil_data = json.load(f)

    rozee_csv_path = "Scrapping/Scrappers/Data/pakistan_jobs.csv"  # just pass path (CSV is handled inside cleaner)

    data = merge_all_sources(jobz_data, mustakbil_data, rozee_csv_path)

  