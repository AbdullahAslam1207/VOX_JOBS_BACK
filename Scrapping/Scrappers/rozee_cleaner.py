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




if __name__ == "__main__":
    data = clean_rozee_csv("pakistan_jobs.csv")

    # Save to JSON
    with open("rozee_cleaned.json", "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

    print("✅ Saved cleaned Rozee data to rozee_cleaned.json")
