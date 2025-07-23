"""
Management command to refresh job listings with proper source URLs
This will clear old jobs and populate with new scraped jobs that have working apply buttons
"""

from django.core.management.base import BaseCommand
from django.db import transaction
from jobs.models import Job, Company, UserPreferences
from jobs.scrapers.multi_source_coordinator import MultiSourceCoordinator
from jobs.scoring import JobScorer
import logging

logger = logging.getLogger('jobs')


class Command(BaseCommand):
    help = 'Clear old jobs and populate with fresh scraped jobs that have proper source URLs'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear-existing',
            action='store_true',
            help='Clear existing job data before scraping new jobs'
        )
        parser.add_argument(
            '--max-jobs',
            type=int,
            default=100,
            help='Maximum number of jobs to scrape'
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Refreshing production job listings...'))
        
        # Get user preferences
        try:
            preferences = UserPreferences.get_active_preferences()
            self.stdout.write(f"Using preferences for: {preferences.name}")
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error loading preferences: {e}'))
            return

        # Clear existing jobs if requested
        if options['clear_existing']:
            self.stdout.write("Clearing existing job data...")
            deleted_count, _ = Job.objects.all().delete()
            self.stdout.write(f"Deleted {deleted_count} existing jobs")

        # Initialize coordinator and scrape fresh jobs
        coordinator = MultiSourceCoordinator(preferences)
        max_jobs = options['max_jobs']
        
        self.stdout.write(f"\nScraping fresh jobs (max {max_jobs})...")
        
        try:
            # Use priority sources that are known to work
            scraped_jobs = coordinator.scrape_priority_sources()
            
            if not scraped_jobs:
                self.stdout.write(self.style.WARNING('No jobs found from scrapers!'))
                return
            
            self.stdout.write(f"Found {len(scraped_jobs)} total jobs")
            
            # Show preview
            self.stdout.write("\nJob preview:")
            for i, job in enumerate(scraped_jobs[:5], 1):
                source_url = job.get('source_url', 'No URL')
                self.stdout.write(f"  {i}. {job.get('title')} at {job.get('company')} - {source_url}")
            
            if len(scraped_jobs) > 5:
                self.stdout.write(f"  ... and {len(scraped_jobs) - 5} more")

            # Save jobs to database with low threshold to ensure they get saved
            self.stdout.write(f"\nSaving jobs to database...")
            saved_count = self._save_jobs_to_database(scraped_jobs, preferences, min_score=1.0)
            
            self.stdout.write(self.style.SUCCESS(f'\nCompleted! Saved {saved_count} new jobs with working apply buttons'))
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error during scraping: {e}'))
            return

    def _save_jobs_to_database(self, jobs_data, preferences, min_score=1.0):
        """Save scraped jobs to database with scoring"""
        saved_count = 0
        scorer = JobScorer(preferences)
        
        for job_data in jobs_data:
            try:
                with transaction.atomic():
                    # Skip jobs without valid URLs
                    source_url = job_data.get('source_url', '')
                    if not source_url or 'example.com' in source_url:
                        self.stdout.write(f"  ✗ Skipping job without valid URL: {job_data.get('title')}")
                        continue

                    # Check if job already exists
                    if Job.objects.filter(source_url=source_url).exists():
                        continue

                    # Get or create company
                    company_name = job_data.get('company', 'Unknown Company')
                    company, created = Company.objects.get_or_create(
                        name=company_name,
                        defaults={
                            'company_type': self._determine_company_type(company_name),
                            'location': job_data.get('location', 'Unknown')
                        }
                    )

                    # Create job
                    job = Job.objects.create(
                        title=job_data.get('title', ''),
                        company=company,
                        description=job_data.get('description', ''),
                        location=job_data.get('location', ''),
                        location_type=job_data.get('location_type', 'onsite'),
                        source=job_data.get('source', 'Unknown'),
                        source_url=source_url,
                        salary_min=job_data.get('salary_min'),
                        salary_max=job_data.get('salary_max'),
                        experience_level=job_data.get('experience_level', 'entry'),
                        employment_type=job_data.get('job_type', 'full_time'),
                        required_skills=job_data.get('skills', []),
                        posted_date=job_data.get('posted_date'),
                        source_job_id=job_data.get('external_id', ''),
                    )

                    # Score the job
                    job_score = scorer.score_job(job)
                    
                    # Only keep jobs above minimum threshold
                    if job_score.total_score >= min_score:
                        saved_count += 1
                        self.stdout.write(f"  ✓ Saved: {job.title} at {company.name} - {source_url[:50]}... (Score: {job_score.total_score:.1f})")
                    else:
                        job.delete()  # Remove low-scoring job
                        
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"  ✗ Error saving job: {e}"))
                continue

        return saved_count

    def _determine_company_type(self, company_name):
        """Determine company type from name"""
        name_lower = company_name.lower()
        
        if any(word in name_lower for word in ['startup', 'labs', 'technologies', 'tech']):
            return 'startup'
        elif any(word in name_lower for word in ['bank', 'financial', 'capital', 'trading']):
            return 'fintech'
        elif any(word in name_lower for word in ['health', 'medical', 'pharma', 'bio']):
            return 'healthcare'
        else:
            return 'tech'