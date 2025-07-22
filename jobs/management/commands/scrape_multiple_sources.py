"""
Enhanced scraping command that uses multiple job sources
"""

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from jobs.models import Job, Company, UserPreferences
from jobs.scrapers.multi_source_coordinator import MultiSourceCoordinator
from jobs.scoring import JobScorer
import logging

logger = logging.getLogger('jobs')


class Command(BaseCommand):
    help = 'Scrape jobs from multiple sources using user preferences'

    def add_arguments(self, parser):
        parser.add_argument(
            '--sources',
            type=str,
            default='priority',
            help='Sources to scrape: "all", "priority", or comma-separated list (e.g., "remoteok,indeed")'
        )
        parser.add_argument(
            '--max-jobs',
            type=int,
            default=100,
            help='Maximum number of jobs to scrape across all sources'
        )
        parser.add_argument(
            '--search-terms',
            type=str,
            help='Comma-separated search terms (overrides user preferences)'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be scraped without saving to database'
        )
        parser.add_argument(
            '--min-score',
            type=float,
            help='Override minimum job score threshold (default: use user preference)'
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Starting enhanced multi-source job scraping...'))
        
        # Get user preferences
        try:
            preferences = UserPreferences.get_active_preferences()
            self.stdout.write(f"Using preferences for: {preferences.name}")
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error loading preferences: {e}'))
            return

        # Initialize coordinator
        coordinator = MultiSourceCoordinator(preferences)
        
        # Get source statistics first
        self.stdout.write("\nSource Status:")
        stats = coordinator.get_source_stats()
        for source, status in stats.items():
            self.stdout.write(f"  {source}: {status}")
        
        # Determine which sources to scrape
        sources_option = options['sources'].lower()
        max_jobs = options['max_jobs']
        
        try:
            if sources_option == 'all':
                self.stdout.write(f"\nScraping from ALL sources (max {max_jobs} jobs)...")
                scraped_jobs = coordinator.scrape_all_sources(max_jobs_per_source=max_jobs//4)
            elif sources_option == 'priority':
                self.stdout.write(f"\nScraping from PRIORITY sources (max {max_jobs} jobs)...")
                scraped_jobs = coordinator.scrape_priority_sources()
            else:
                # Custom search terms
                if options['search_terms']:
                    search_terms = [term.strip() for term in options['search_terms'].split(',')]
                    self.stdout.write(f"\nTargeted search for: {search_terms}")
                    scraped_jobs = coordinator.scrape_targeted_search(search_terms, max_jobs)
                else:
                    self.stdout.write(f"\nScraping from priority sources...")
                    scraped_jobs = coordinator.scrape_priority_sources()

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error during scraping: {e}'))
            return

        if not scraped_jobs:
            self.stdout.write(self.style.WARNING('No jobs found!'))
            return

        self.stdout.write(f"\nFound {len(scraped_jobs)} total jobs")
        
        # Show preview
        self.stdout.write("\nJob preview:")
        for i, job in enumerate(scraped_jobs[:5], 1):
            self.stdout.write(f"  {i}. {job.get('title')} at {job.get('company')} ({job.get('source')})")
        
        if len(scraped_jobs) > 5:
            self.stdout.write(f"  ... and {len(scraped_jobs) - 5} more")

        if options['dry_run']:
            self.stdout.write(self.style.WARNING('\nDRY RUN: No jobs saved to database'))
            return

        # Save jobs to database
        self.stdout.write(f"\nSaving jobs to database...")
        saved_count = self._save_jobs_to_database(scraped_jobs, preferences, options.get('min_score'))
        
        self.stdout.write(self.style.SUCCESS(f'\nCompleted! Saved {saved_count} new jobs to database'))

    def _save_jobs_to_database(self, jobs_data, preferences, min_score_override=None):
        """Save scraped jobs to database with scoring"""
        saved_count = 0
        scorer = JobScorer(preferences)
        
        # Use override score if provided
        min_score = min_score_override if min_score_override is not None else preferences.min_job_score_threshold
        
        for job_data in jobs_data:
            try:
                with transaction.atomic():
                    # Check if job already exists
                    source_url = job_data.get('source_url', '')
                    if not source_url or Job.objects.filter(source_url=source_url).exists():
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
                    
                    # Only keep jobs above threshold
                    if job_score.total_score >= min_score:
                        saved_count += 1
                        self.stdout.write(f"  ✓ Saved: {job.title} at {company.name} (Score: {job_score.total_score:.1f})")
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