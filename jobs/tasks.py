"""
Celery tasks for automated job scraping and processing
"""

import logging
from celery import shared_task
from django.utils import timezone
from datetime import datetime, timedelta

from .models import Job, JobScore, EmailDigest
from .scrapers.multi_source_scraper import EnhancedJobScraper
from .scoring import JobScorer
from .email_digest import EmailDigestManager

logger = logging.getLogger('jobs')

@shared_task
def scrape_jobs_task(source='indeed', location='New York, NY', limit=50):
    """Background task to scrape jobs from various sources"""
    try:
        logger.info(f"Starting job scraping task: {source} in {location}")
        
        # Define search terms based on user requirements
        search_terms = [
            "Python Developer",
            "Django Developer", 
            "Backend Developer",
            "Full Stack Developer",
            "Junior Python Developer",
            "Entry Level Developer",
            "Python Engineer",
            "Django Web Developer"
        ]
        
        # Initialize scraper
        scraper = EnhancedJobScraper()
        jobs_data = scraper.scrape_jobs(search_terms[:4], location)  # Limit for performance
        
        created_count = 0
        processed_count = 0
        
        for job_data in jobs_data[:limit]:
            try:
                # Get or create company
                from .models import Company
                company, _ = Company.objects.get_or_create(
                    name=job_data['company_name'],
                    defaults={
                        'location': location,
                        'company_type': 'unknown'
                    }
                )
                
                # Check if job already exists
                if Job.objects.filter(source_url=job_data['source_url']).exists():
                    logger.debug(f"Job already exists: {job_data['title']}")
                    continue
                
                # Create new job
                job = Job.objects.create(
                    title=job_data['title'],
                    company=company,
                    description=job_data['description'],
                    location=job_data['location'],
                    location_type=job_data['location_type'],
                    source=job_data['source'],
                    source_url=job_data['source_url'],
                    required_skills=job_data['required_skills'],
                    salary_min=job_data['salary_min'],
                    salary_max=job_data['salary_max'],
                    experience_level=job_data['experience_level'],
                    posted_date=job_data['posted_date'],
                    is_entry_level_friendly=job_data['is_entry_level_friendly'],
                    employment_type=job_data['employment_type']
                )
                
                # Create initial job score placeholder
                JobScore.objects.create(job=job)
                
                created_count += 1
                processed_count += 1
                
                logger.debug(f"Created job: {job.title} at {job.company.name}")
                
            except Exception as e:
                logger.error(f"Error creating job: {str(e)}")
                continue
        
        logger.info(f"Job scraping completed: {created_count} new jobs created, {processed_count} processed")
        
        # Trigger scoring task for new jobs
        if created_count > 0:
            score_jobs_task.delay()
        
        return {
            'status': 'success',
            'created_count': created_count,
            'processed_count': processed_count
        }
        
    except Exception as e:
        logger.error(f"Error in scrape_jobs_task: {str(e)}")
        return {
            'status': 'error',
            'error': str(e)
        }

@shared_task
def score_jobs_task(rescore_all=False):
    """Background task to score jobs based on user preferences"""
    try:
        logger.info(f"Starting job scoring task (rescore_all={rescore_all})")
        
        scorer = JobScorer()
        
        if rescore_all:
            scored_count = scorer.rescore_all_jobs()
        else:
            scored_count = scorer.score_all_jobs()
        
        logger.info(f"Job scoring completed: {scored_count} jobs scored")
        
        return {
            'status': 'success',
            'scored_count': scored_count
        }
        
    except Exception as e:
        logger.error(f"Error in score_jobs_task: {str(e)}")
        return {
            'status': 'error',
            'error': str(e)
        }

@shared_task
def send_daily_digest_task():
    """Background task to send daily email digest"""
    try:
        logger.info("Starting daily email digest task")
        
        digest_manager = EmailDigestManager()
        success = digest_manager.send_digest()
        
        if success:
            logger.info("Daily email digest sent successfully")
            return {
                'status': 'success',
                'message': 'Email digest sent successfully'
            }
        else:
            logger.warning("Daily email digest was not sent (not enough quality jobs)")
            return {
                'status': 'skipped',
                'message': 'Not enough quality jobs for digest'
            }
        
    except Exception as e:
        logger.error(f"Error in send_daily_digest_task: {str(e)}")
        return {
            'status': 'error',
            'error': str(e)
        }

@shared_task
def cleanup_old_jobs_task(days=30):
    """Background task to clean up old job postings"""
    try:
        logger.info(f"Starting cleanup task for jobs older than {days} days")
        
        cutoff_date = timezone.now() - timedelta(days=days)
        
        # Deactivate old jobs instead of deleting them
        old_jobs = Job.objects.filter(
            scraped_at__lt=cutoff_date,
            is_active=True
        )
        
        count = old_jobs.count()
        old_jobs.update(is_active=False)
        
        logger.info(f"Cleanup completed: {count} jobs deactivated")
        
        return {
            'status': 'success',
            'deactivated_count': count
        }
        
    except Exception as e:
        logger.error(f"Error in cleanup_old_jobs_task: {str(e)}")
        return {
            'status': 'error', 
            'error': str(e)
        }

@shared_task
def daily_automation_task():
    """Master task that runs daily automation sequence"""
    try:
        logger.info("Starting daily automation sequence")
        
        # 1. Scrape new jobs
        scrape_result = scrape_jobs_task.delay()
        
        # 2. Wait a bit for scraping to complete, then score jobs
        # In production, you'd want to chain these tasks properly
        from time import sleep
        sleep(10)  # Wait for scraping to complete
        
        score_result = score_jobs_task.delay()
        
        # 3. Send digest if it's evening
        current_hour = timezone.now().hour
        if current_hour == 19:  # 7 PM
            digest_result = send_daily_digest_task.delay()
        
        # 4. Cleanup old jobs weekly (Sunday)
        if timezone.now().weekday() == 6:  # Sunday
            cleanup_result = cleanup_old_jobs_task.delay()
        
        logger.info("Daily automation sequence initiated")
        
        return {
            'status': 'success',
            'message': 'Daily automation sequence started'
        }
        
    except Exception as e:
        logger.error(f"Error in daily_automation_task: {str(e)}")
        return {
            'status': 'error',
            'error': str(e)
        }

@shared_task
def health_check_task():
    """Task to check system health and send alerts if needed"""
    try:
        logger.info("Running system health check")
        
        # Check recent job scraping
        recent_jobs = Job.objects.filter(
            scraped_at__gte=timezone.now() - timedelta(days=1)
        ).count()
        
        # Check scoring health
        unscored_jobs = Job.objects.filter(
            is_active=True,
            score__isnull=True
        ).count()
        
        # Check recent email digests
        recent_digests = EmailDigest.objects.filter(
            sent_at__gte=timezone.now() - timedelta(days=7),
            email_sent_successfully=True
        ).count()
        
        health_report = {
            'recent_jobs_scraped': recent_jobs,
            'unscored_jobs': unscored_jobs,
            'recent_successful_digests': recent_digests,
            'timestamp': timezone.now().isoformat()
        }
        
        # Log warnings if issues found
        if recent_jobs == 0:
            logger.warning("No jobs scraped in the last 24 hours")
        
        if unscored_jobs > 10:
            logger.warning(f"{unscored_jobs} unscored jobs found")
        
        if recent_digests == 0:
            logger.warning("No successful email digests in the last week")
        
        logger.info(f"Health check completed: {health_report}")
        
        return {
            'status': 'success',
            'health_report': health_report
        }
        
    except Exception as e:
        logger.error(f"Error in health_check_task: {str(e)}")
        return {
            'status': 'error',
            'error': str(e)
        }