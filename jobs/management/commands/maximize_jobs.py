"""
Management command to maximize job listings by any means necessary
Focuses on working scrapers and gets maximum jobs possible
"""

from django.core.management.base import BaseCommand
from django.db import transaction
from jobs.models import Job, Company, UserPreferences
from jobs.scrapers.remoteok_scraper import RemoteOKScraper
from jobs.scrapers.python_jobs_scraper import PythonJobsScraper
from jobs.scrapers.wellfound_scraper import WellfoundScraper
from jobs.scoring import JobScorer
import logging

logger = logging.getLogger('jobs')


class Command(BaseCommand):
    help = 'Maximize job listings by getting as many as possible from working sources'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear-existing',
            action='store_true',
            help='Clear existing jobs before scraping'
        )
        parser.add_argument(
            '--min-score',
            type=float,
            default=0.1,
            help='Minimum score threshold (very low to maximize jobs)'
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('🚀 MAXIMIZING JOB LISTINGS - Getting as many as possible!'))
        
        # Get preferences
        try:
            preferences = UserPreferences.get_active_preferences()
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error loading preferences: {e}'))
            return

        # Clear existing if requested
        if options['clear_existing']:
            old_count = Job.objects.count()
            Job.objects.all().delete()
            self.stdout.write(f"🗑️  Cleared {old_count} existing jobs")

        min_score = options['min_score']
        self.stdout.write(f"⚡ Using very low score threshold: {min_score} to maximize results")

        all_scraped_jobs = []

        # 1. REMOTEOK - Most reliable source
        self.stdout.write("\n🎯 STEP 1: RemoteOK (Most reliable)")
        remoteok_scraper = RemoteOKScraper(preferences)
        
        # Try multiple search strategies
        search_strategies = [
            ['python', 'django', 'backend'],
            ['javascript', 'react', 'frontend'], 
            ['full stack', 'fullstack', 'software engineer'],
            ['data', 'machine learning', 'ai'],
            ['devops', 'cloud', 'aws'],
            ['nodejs', 'node.js', 'typescript'],
        ]
        
        for strategy in search_strategies:
            try:
                jobs = remoteok_scraper.scrape_jobs(strategy)
                self.stdout.write(f"  📦 Found {len(jobs)} jobs for: {', '.join(strategy)}")
                all_scraped_jobs.extend(jobs)
            except Exception as e:
                self.stdout.write(f"  ❌ Error with {strategy}: {e}")
                continue

        # 2. WELLFOUND - Startup jobs
        self.stdout.write("\n🏢 STEP 2: Wellfound (Startup jobs)")
        wellfound_scraper = WellfoundScraper(preferences)
        
        startup_searches = [
            ['Software Engineer', 'Backend Engineer'],
            ['Full Stack Engineer', 'Frontend Engineer'],
            ['Python Developer', 'Django Developer'],
        ]
        
        for search_terms in startup_searches:
            for location in ['New York', 'San Francisco', 'Remote']:
                try:
                    jobs = wellfound_scraper.scrape_jobs(search_terms, location)
                    self.stdout.write(f"  🏗️  Found {len(jobs)} jobs for: {', '.join(search_terms)} in {location}")
                    all_scraped_jobs.extend(jobs)
                except Exception as e:
                    continue

        # 3. PYTHON.ORG - Python-specific jobs
        self.stdout.write("\n🐍 STEP 3: Python.org (Python-specific)")
        python_scraper = PythonJobsScraper(preferences)
        
        python_searches = [
            ['python', 'django', 'web development'],
            ['data science', 'machine learning', 'ai'],
            ['backend', 'api', 'web services'],
        ]
        
        for search_terms in python_searches:
            try:
                jobs = python_scraper.scrape_jobs(search_terms)
                self.stdout.write(f"  🔬 Found {len(jobs)} jobs for: {', '.join(search_terms)}")
                all_scraped_jobs.extend(jobs)
            except Exception as e:
                continue

        # Remove duplicates based on URL
        unique_jobs = []
        seen_urls = set()
        
        for job in all_scraped_jobs:
            url = job.get('source_url', '')
            if url and url not in seen_urls and 'example.com' not in url:
                seen_urls.add(url)
                unique_jobs.append(job)

        self.stdout.write(f"\n📊 SUMMARY:")
        self.stdout.write(f"  Total scraped: {len(all_scraped_jobs)} jobs")
        self.stdout.write(f"  After dedup: {len(unique_jobs)} unique jobs")

        # Save with very low threshold
        self.stdout.write(f"\n💾 SAVING JOBS (min score: {min_score})...")
        saved_count = self._save_jobs_to_database(unique_jobs, preferences, min_score)
        
        final_total = Job.objects.count()
        self.stdout.write(self.style.SUCCESS(f'\n🎉 MAXIMIZATION COMPLETE!'))
        self.stdout.write(self.style.SUCCESS(f'   ✅ Saved: {saved_count} new jobs'))
        self.stdout.write(self.style.SUCCESS(f'   📈 Total in database: {final_total} jobs'))

    def _save_jobs_to_database(self, jobs_data, preferences, min_score):
        """Save jobs with very permissive scoring"""
        saved_count = 0
        scorer = JobScorer(preferences)
        
        for job_data in jobs_data:
            try:
                with transaction.atomic():
                    source_url = job_data.get('source_url', '')
                    if not source_url or 'example.com' in source_url:
                        continue

                    # Skip if exists
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
                        location_type=job_data.get('location_type', 'remote'),
                        source=job_data.get('source', 'Unknown'),
                        source_url=source_url,
                        salary_min=job_data.get('salary_min'),
                        salary_max=job_data.get('salary_max'),
                        experience_level=job_data.get('experience_level', 'junior'),
                        employment_type=job_data.get('job_type', 'full_time'),
                        required_skills=job_data.get('skills', []),
                        posted_date=job_data.get('posted_date'),
                        source_job_id=job_data.get('external_id', ''),
                    )

                    # Score but be very permissive
                    job_score = scorer.score_job(job)
                    
                    if job_score.total_score >= min_score:
                        saved_count += 1
                        self.stdout.write(f"  ✅ {job.title} at {company.name} (Score: {job_score.total_score:.1f})")
                    else:
                        job.delete()
                        
            except Exception as e:
                continue

        return saved_count

    def _determine_company_type(self, company_name):
        """Simple company type classification"""
        name_lower = company_name.lower()
        
        if any(word in name_lower for word in ['startup', 'labs', 'technologies']):
            return 'startup'
        elif any(word in name_lower for word in ['bank', 'financial', 'capital']):
            return 'fintech'
        else:
            return 'tech'