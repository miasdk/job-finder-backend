"""
Comprehensive job expansion command to get better job coverage
Runs all available scrapers in priority order
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from jobs.models import Job, Company, UserPreferences
from jobs.scoring import JobScorer
from jobs.scrapers.multi_source_coordinator import MultiSourceCoordinator
import logging

logger = logging.getLogger('jobs')

class Command(BaseCommand):
    help = 'Expand job listings by running all available scrapers comprehensively'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear-existing',
            action='store_true',
            help='Clear existing jobs before scraping new ones',
        )
        parser.add_argument(
            '--min-score',
            type=float,
            default=15.0,
            help='Minimum score threshold for saving jobs (default: 15.0)',
        )
        parser.add_argument(
            '--max-jobs',
            type=int,
            default=200,
            help='Maximum total jobs to collect (default: 200)',
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('🚀 EXPANDING JOB SOURCES - Comprehensive scraping from all sources!'))
        
        # Get user preferences
        try:
            preferences = UserPreferences.get_active_preferences()
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error loading preferences: {e}'))
            return

        # Clear existing jobs if requested
        if options['clear_existing']:
            old_count = Job.objects.count()
            Job.objects.all().delete()
            self.stdout.write(f"🗑️  Cleared {old_count} existing jobs")

        min_score = options['min_score']
        max_jobs = options['max_jobs']
        
        self.stdout.write(f"⚡ Using low score threshold: {min_score} to maximize results")
        self.stdout.write(f"📊 Target: {max_jobs} total jobs")

        # Initialize multi-source coordinator
        coordinator = MultiSourceCoordinator(preferences)
        
        # Enhanced search strategy with more comprehensive terms
        enhanced_search_terms = [
            # From user preferences
            *preferences.job_titles,
            *preferences.skills[:5],  # Top 5 skills
            
            # Additional comprehensive terms
            'Software Engineer',
            'Developer',
            'Python Developer', 
            'Django Developer',
            'Full Stack Developer',
            'Backend Developer',
            'Junior Developer',
            'Entry Level Developer',
            'Software Engineer Entry Level',
            'Junior Software Engineer',
            'Associate Developer',
            'Junior Python',
            'Python Junior',
            'Entry Level Python',
            'Graduate Developer',
            'New Grad Developer',
        ]

        # Remove duplicates while preserving order
        seen = set()
        unique_search_terms = []
        for term in enhanced_search_terms:
            if term.lower() not in seen:
                seen.add(term.lower())
                unique_search_terms.append(term)

        self.stdout.write(f"🔍 Using {len(unique_search_terms)} search terms: {unique_search_terms[:5]}...")

        # Enhanced location strategy
        enhanced_locations = [
            *preferences.preferred_locations,
            'Remote',
            'New York',
            'NYC', 
            'New York City',
            'Manhattan',
            'Brooklyn',
            'USA',
            'United States'
        ]
        
        # Remove duplicates
        unique_locations = list(dict.fromkeys(enhanced_locations))
        
        self.stdout.write(f"📍 Searching in {len(unique_locations)} locations: {unique_locations}")

        all_scraped_jobs = []
        
        # Strategy 1: Priority API sources (highest quality)
        self.stdout.write("\n🌟 STEP 1: Priority API Sources (JSearch, Adzuna, Reed, Rise)")
        api_sources = ['jsearch', 'adzuna', 'reed', 'rise']
        
        for source_name in api_sources:
            if source_name in coordinator.scrapers:
                try:
                    scraper = coordinator.scrapers[source_name]
                    
                    # Use multiple search strategies for APIs
                    for search_term in unique_search_terms[:8]:  # Use more terms for APIs
                        for location in unique_locations[:4]:  # Multiple locations
                            try:
                                jobs = scraper.scrape_jobs([search_term], location)
                                self.stdout.write(f"  ✅ {source_name}: '{search_term}' in '{location}' → {len(jobs)} jobs")
                                all_scraped_jobs.extend(jobs)
                                
                                if len(all_scraped_jobs) >= max_jobs:
                                    break
                            except Exception as e:
                                self.stdout.write(f"  ⚠️ {source_name} error for '{search_term}' in '{location}': {e}")
                                continue
                        
                        if len(all_scraped_jobs) >= max_jobs:
                            break
                            
                except Exception as e:
                    self.stdout.write(f"  ❌ {source_name} initialization error: {e}")
                    continue

        # Strategy 2: Remote-focused sources  
        self.stdout.write("\n🌐 STEP 2: Remote Job Specialists (RemoteOK)")
        remote_sources = ['remoteok']
        
        for source_name in remote_sources:
            if source_name in coordinator.scrapers and len(all_scraped_jobs) < max_jobs:
                try:
                    scraper = coordinator.scrapers[source_name]
                    
                    # RemoteOK works well with multiple search terms
                    remote_terms = [term for term in unique_search_terms if 'remote' not in term.lower()][:6]
                    jobs = scraper.scrape_jobs(remote_terms[:4])
                    self.stdout.write(f"  ✅ {source_name}: {len(jobs)} remote jobs")
                    all_scraped_jobs.extend(jobs)
                    
                except Exception as e:
                    self.stdout.write(f"  ❌ {source_name} error: {e}")

        # Strategy 3: Python-specific sources
        self.stdout.write("\n🐍 STEP 3: Python-Specific Sources (Python.org)")
        python_sources = ['python_jobs']
        
        for source_name in python_sources:
            if source_name in coordinator.scrapers and len(all_scraped_jobs) < max_jobs:
                try:
                    scraper = coordinator.scrapers[source_name]
                    
                    python_terms = ['django', 'python', 'backend', 'web developer']
                    jobs = scraper.scrape_jobs(python_terms)
                    self.stdout.write(f"  ✅ {source_name}: {len(jobs)} Python jobs")
                    all_scraped_jobs.extend(jobs)
                    
                except Exception as e:
                    self.stdout.write(f"  ❌ {source_name} error: {e}")

        # Strategy 4: Startup job sources
        self.stdout.write("\n🚀 STEP 4: Startup Sources (Wellfound)")
        startup_sources = ['wellfound']
        
        for source_name in startup_sources:
            if source_name in coordinator.scrapers and len(all_scraped_jobs) < max_jobs:
                try:
                    scraper = coordinator.scrapers[source_name]
                    
                    startup_terms = ['software engineer', 'developer', 'full stack', 'backend']
                    for location in ['New York', 'Remote']:
                        jobs = scraper.scrape_jobs(startup_terms[:2], location)
                        self.stdout.write(f"  ✅ {source_name}: {len(jobs)} startup jobs in {location}")
                        all_scraped_jobs.extend(jobs)
                        
                except Exception as e:
                    self.stdout.write(f"  ❌ {source_name} error: {e}")

        # Strategy 5: General job boards (Indeed with Selenium)
        self.stdout.write("\n🔍 STEP 5: General Job Boards (Indeed)")
        general_sources = ['indeed_selenium', 'indeed']
        
        for source_name in general_sources:
            if source_name in coordinator.scrapers and len(all_scraped_jobs) < max_jobs:
                try:
                    scraper = coordinator.scrapers[source_name]
                    
                    # Indeed works better with specific terms
                    indeed_terms = ['junior python developer', 'entry level python', 'python django']
                    for term in indeed_terms[:2]:
                        for location in ['New York', 'Remote']:
                            try:
                                jobs = scraper.scrape_jobs([term], location)
                                self.stdout.write(f"  ✅ {source_name}: '{term}' in '{location}' → {len(jobs)} jobs")
                                all_scraped_jobs.extend(jobs)
                            except Exception as e:
                                self.stdout.write(f"  ⚠️ {source_name} error for '{term}': {e}")
                                continue
                                
                except Exception as e:
                    self.stdout.write(f"  ❌ {source_name} error: {e}")

        # Deduplicate and filter jobs
        self.stdout.write(f"\n📊 PROCESSING {len(all_scraped_jobs)} total scraped jobs...")
        
        unique_jobs = coordinator._deduplicate_jobs(all_scraped_jobs)
        self.stdout.write(f"✨ {len(unique_jobs)} unique jobs after deduplication")

        # Score and save jobs with lower thresholds
        scorer = JobScorer(preferences)
        saved_count = 0
        low_score_count = 0
        
        for job_data in unique_jobs:
            try:
                # Skip jobs with invalid URLs
                source_url = job_data.get('source_url', '')
                if not source_url or 'example.com' in source_url:
                    continue
                    
                # Skip if job already exists
                if Job.objects.filter(source_url=source_url).exists():
                    continue
                
                # Get or create company
                company, created = Company.objects.get_or_create(
                    name=job_data.get('company', 'Unknown'),
                    defaults={
                        'company_type': 'tech', 
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
                    experience_level=job_data.get('experience_level', 'entry'),
                    employment_type=job_data.get('job_type', 'full_time'),
                    required_skills=job_data.get('skills', []),
                    posted_date=job_data.get('posted_date'),
                )
                
                # Score the job
                job_score = scorer.score_job(job)
                
                if job_score.total_score >= min_score:
                    saved_count += 1
                    self.stdout.write(f"  ✅ Saved: {job.title} at {job.company.name} (Score: {job_score.total_score:.1f})")
                else:
                    low_score_count += 1
                    job.delete()  # Remove low-scoring jobs
                    
            except Exception as e:
                self.stdout.write(f"  ⚠️ Error processing job: {e}")
                continue

        # Final results
        total_jobs = Job.objects.count()
        recommended_jobs = Job.objects.filter(score__recommended_for_application=True).count()
        meets_minimum = Job.objects.filter(score__meets_minimum_requirements=True).count()
        
        self.stdout.write(self.style.SUCCESS(f'\n🎉 JOB EXPANSION COMPLETE!'))
        self.stdout.write(f'📈 Added {saved_count} new jobs (rejected {low_score_count} low-scoring)')
        self.stdout.write(f'📊 Total jobs in database: {total_jobs}')
        self.stdout.write(f'⭐ AI recommended: {recommended_jobs}')
        self.stdout.write(f'✅ Meet requirements: {meets_minimum}')
        self.stdout.write(f'🎯 Success rate: {(saved_count/len(unique_jobs)*100):.1f}%' if unique_jobs else '0%') 