from django.core.management.base import BaseCommand
from django.utils import timezone
from jobs.models import Job, Company, JobScore
from jobs.scrapers.indeed_scraper import IndeedRSScraper
import logging

logger = logging.getLogger('jobs')

class Command(BaseCommand):
    help = 'Scrape jobs from various sources'

    def add_arguments(self, parser):
        parser.add_argument(
            '--source',
            type=str,
            default='indeed',
            help='Job source to scrape (indeed, stackoverflow, angellist)'
        )
        parser.add_argument(
            '--location',
            type=str,
            default='New York, NY',
            help='Location to search for jobs'
        )
        parser.add_argument(
            '--limit',
            type=int,
            default=50,
            help='Maximum number of jobs to scrape'
        )

    def handle(self, *args, **options):
        source = options['source']
        location = options['location']
        limit = options['limit']
        
        self.stdout.write(f"Starting job scraping from {source} in {location}...")
        
        # Define search terms based on user requirements
        search_terms = [
            "Python Developer",
            "Django Developer",
            "Backend Developer",
            "Full Stack Developer",
            "Junior Python Developer",
            "Entry Level Developer",
            "React Developer",
            "Full Stack Engineer",
            "Python Engineer",
            "Backend Engineer"
        ]
        
        scraped_count = 0
        new_jobs_count = 0
        
        try:
            if source == 'indeed':
                from jobs.scrapers.multi_source_scraper import MultiSourceScraper
                scraper = MultiSourceScraper()
                jobs_data = scraper.scrape_jobs(search_terms[:3], location)  # Use real scrapers
                
                for job_data in jobs_data[:limit]:
                    try:
                        # Get or create company
                        company_name = job_data.get('company', job_data.get('company_name', 'Unknown Company'))
                        company, created = Company.objects.get_or_create(
                            name=company_name,
                            defaults={
                                'location': location,
                                'company_type': 'unknown'
                            }
                        )
                        
                        if created:
                            self.stdout.write(f"Created new company: {company.name}")
                        
                        # Check if job already exists
                        existing_job = Job.objects.filter(
                            source_url=job_data['source_url']
                        ).first()
                        
                        if existing_job:
                            self.stdout.write(f"Job already exists: {existing_job.title}")
                            continue
                        
                        # Create new job
                        job = Job.objects.create(
                            title=job_data.get('title', 'Untitled Job'),
                            company=company,
                            description=job_data.get('description', ''),
                            location=job_data.get('location', location),
                            location_type=job_data.get('location_type', 'onsite'),
                            source=job_data.get('source', 'unknown'),
                            source_url=job_data.get('source_url', ''),
                            required_skills=job_data.get('skills', job_data.get('required_skills', [])),
                            salary_min=job_data.get('salary_min'),
                            salary_max=job_data.get('salary_max'),
                            experience_level=job_data.get('experience_level', 'junior'),
                            posted_date=job_data.get('posted_date') or timezone.now(),
                            is_entry_level_friendly=job_data.get('is_entry_level_friendly', True),
                            employment_type=job_data.get('job_type', job_data.get('employment_type', 'full_time'))
                        )
                        
                        # Create initial job score (will be calculated later)
                        JobScore.objects.create(job=job)
                        
                        new_jobs_count += 1
                        scraped_count += 1
                        
                        self.stdout.write(f"Created job: {job.title} at {job.company.name}")
                        
                    except Exception as e:
                        self.stdout.write(
                            self.style.ERROR(f"Error creating job: {str(e)}")
                        )
                        continue
            
            else:
                self.stdout.write(
                    self.style.ERROR(f"Unsupported source: {source}")
                )
                return
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"Error during scraping: {str(e)}")
            )
            return
        
        self.stdout.write(
            self.style.SUCCESS(
                f"Scraping completed! Processed {scraped_count} jobs, created {new_jobs_count} new jobs."
            )
        )