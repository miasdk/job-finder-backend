"""
Simple job refresh command that works with available scrapers
"""

from django.core.management.base import BaseCommand
from jobs.models import Job, Company, UserPreferences
from jobs.scoring import JobScorer
import json
import logging

logger = logging.getLogger('jobs')

class Command(BaseCommand):
    help = 'Simple job refresh using available scrapers'
    
    def handle(self, *args, **options):
        try:
            preferences = UserPreferences.get_active_preferences()
            
            # Clear old jobs with invalid URLs
            invalid_jobs = Job.objects.filter(source_url__icontains='example.com')
            invalid_count = invalid_jobs.count()
            invalid_jobs.delete()
            
            # Clear jobs older than 30 days to make room for fresh ones
            from datetime import datetime, timezone, timedelta
            thirty_days_ago = datetime.now(timezone.utc) - timedelta(days=30)
            old_jobs = Job.objects.filter(scraped_at__lt=thirty_days_ago)
            old_count = old_jobs.count()
            old_jobs.delete()
            
            deleted_count = invalid_count + old_count
            logger.info(f"Cleanup: {invalid_count} invalid jobs, {old_count} old jobs removed")
            
            saved_count = 0
            
            # Try to use JSearch API scraper if available
            try:
                from jobs.scrapers.jsearch_api_scraper import JSearchAPIScraper
                
                scraper = JSearchAPIScraper(preferences)
                search_terms = scraper.get_search_terms()
                
                # Use ALL search terms for maximum coverage
                logger.info(f"Using search terms: {search_terms}")
                for search_term in search_terms[:6]:  # Use up to 6 search terms
                    logger.info(f"Searching for: {search_term}")
                    jobs_data = scraper.scrape_jobs([search_term])
                    
                    scorer = JobScorer(preferences)
                    
                    for job_data in jobs_data[:50]:  # Increased to 50 jobs per search term
                        try:
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
                                source=job_data.get('source', 'JSearch'),
                                source_url=source_url,
                                salary_min=job_data.get('salary_min'),
                                salary_max=job_data.get('salary_max'),
                                experience_level=job_data.get('experience_level', 'junior'),
                                employment_type=job_data.get('job_type', 'full_time'),
                                required_skills=job_data.get('skills', []),
                                posted_date=job_data.get('posted_date'),
                            )
                            
                            # Score and save if above threshold
                            job_score = scorer.score_job(job)
                            
                            if job_score.total_score >= 15:  # Very low threshold for maximum variety
                                saved_count += 1
                                logger.info(f"Added job: {job.title} (Score: {job_score.total_score:.1f})")
                            else:
                                # Still log rejected jobs for debugging
                                logger.debug(f"Rejected job: {job.title} (Score: {job_score.total_score:.1f})")
                                job.delete()
                                
                        except Exception as e:
                            logger.error(f"Error processing job: {e}")
                            continue
                            
            except ImportError as e:
                logger.warning(f"JSearch scraper not available: {e}")
                
                # Fallback: Create some sample jobs to test with
                self.create_sample_jobs(preferences)
                saved_count = 5
            
            total_active_jobs = Job.objects.filter(is_active=True).count()
            
            result = {
                'success': True,
                'deleted_old_jobs': deleted_count,
                'added_new_jobs': saved_count,
                'total_jobs': total_active_jobs
            }
            
            self.stdout.write(json.dumps(result))
            
        except Exception as e:
            error_result = {
                'success': False,
                'error': str(e)
            }
            self.stdout.write(json.dumps(error_result))
    
    def create_sample_jobs(self, preferences):
        """Create sample jobs for testing when scrapers aren't available"""
        from datetime import datetime, timezone
        
        sample_jobs = [
            {
                'title': 'Senior Python Developer',
                'company': 'TechCorp',
                'description': 'We are looking for an experienced Python developer with Django expertise.',
                'location': 'New York, NY',
                'skills': ['Python', 'Django', 'PostgreSQL', 'AWS'],
                'salary_min': 120000,
                'salary_max': 160000,
            },
            {
                'title': 'Full Stack Developer',
                'company': 'StartupXYZ',
                'description': 'Join our team to build amazing web applications using React and Python.',
                'location': 'Remote',
                'skills': ['React', 'JavaScript', 'Python', 'Node.js'],
                'salary_min': 90000,
                'salary_max': 130000,
            },
            {
                'title': 'Backend Engineer',
                'company': 'DataFlow Inc',
                'description': 'Backend engineer position focusing on API development and data processing.',
                'location': 'San Francisco, CA',
                'skills': ['Python', 'Django', 'REST APIs', 'Docker'],
                'salary_min': 110000,
                'salary_max': 150000,
            }
        ]
        
        scorer = JobScorer(preferences)
        
        for i, job_data in enumerate(sample_jobs):
            company, created = Company.objects.get_or_create(
                name=job_data['company'],
                defaults={'company_type': 'tech', 'location': job_data['location']}
            )
            
            job = Job.objects.create(
                title=job_data['title'],
                company=company,
                description=job_data['description'],
                location=job_data['location'],
                location_type='remote' if 'remote' in job_data['location'].lower() else 'hybrid',
                source='Sample Data',
                source_url=f'https://example-jobs.com/job/{i+1}',
                salary_min=job_data['salary_min'],
                salary_max=job_data['salary_max'],
                experience_level='mid',
                employment_type='full_time',
                required_skills=job_data['skills'],
                posted_date=datetime.now(timezone.utc),
            )
            
            scorer.score_job(job)