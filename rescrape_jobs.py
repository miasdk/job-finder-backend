#!/usr/bin/env python
"""
Quick script to re-scrape jobs with proper source URLs
"""
import os
import sys
import django
from pathlib import Path

# Add the project directory to Python path
BASE_DIR = Path(__file__).resolve().parent
sys.path.append(str(BASE_DIR))

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'job_finder.settings')
django.setup()

from jobs.scrapers.remoteok_scraper import RemoteOKScraper
from jobs.models import Job, Company, UserPreferences
from jobs.scoring import JobScorer

def rescrape_with_urls():
    """Re-scrape a few jobs to ensure they have proper source URLs"""
    print("Re-scraping jobs with source URLs...")
    
    # Get user preferences for targeted scraping
    prefs = UserPreferences.get_active_preferences()
    
    # Initialize scraper with preferences
    scraper = RemoteOKScraper(prefs)
    
    # Get search terms from preferences
    search_terms = scraper.get_search_terms()[:3]  # Top 3 terms
    print(f"Using search terms: {search_terms}")
    
    # Scrape jobs
    jobs_data = scraper.scrape_jobs(search_terms)
    
    scorer = JobScorer(prefs)
    saved_jobs = 0
    
    for job_data in jobs_data[:10]:  # Limit to 10 jobs to avoid overloading
        try:
            # Check if job already exists
            if Job.objects.filter(source_url=job_data['source_url']).exists():
                continue
            
            # Get or create company
            company, created = Company.objects.get_or_create(
                name=job_data['company'],
                defaults={
                    'company_type': 'tech',  # Default for RemoteOK
                    'location': 'Remote'
                }
            )
            
            # Create job
            job = Job.objects.create(
                title=job_data['title'],
                company=company,
                description=job_data.get('description', ''),
                location=job_data['location'],
                location_type=job_data['location_type'],
                source=job_data['source'],
                source_url=job_data['source_url'],
                salary_min=job_data.get('salary_min'),
                salary_max=job_data.get('salary_max'),
                experience_level=job_data.get('experience_level', 'entry'),
                required_skills=job_data.get('skills', []),
                posted_date=job_data.get('posted_date'),
            )
            
            # Score the job
            scorer.score_job(job)
            saved_jobs += 1
            print(f"Saved: {job.title} at {job.company.name}")
            
        except Exception as e:
            print(f"Error saving job: {e}")
            continue
    
    print(f"Re-scraped and saved {saved_jobs} jobs with proper source URLs")

if __name__ == "__main__":
    rescrape_with_urls()