"""
Multi-source job scraper coordinator
Manages scraping from multiple job sources and combines results
"""

import logging
from typing import List, Dict, Optional
from datetime import datetime, timezone
from .remoteok_scraper import RemoteOKScraper
from .enhanced_indeed_scraper import EnhancedIndeedScraper
from .selenium_indeed_scraper import SeleniumIndeedScraper
from .python_jobs_scraper import PythonJobsScraper
from .wellfound_scraper import WellfoundScraper

logger = logging.getLogger('jobs')


class MultiSourceCoordinator:
    """Coordinates job scraping from multiple sources"""
    
    def __init__(self, user_preferences=None):
        self.user_preferences = user_preferences
        
        # Initialize all scrapers
        self.scrapers = {
            'remoteok': RemoteOKScraper(user_preferences),
            'indeed': EnhancedIndeedScraper(user_preferences),
            'indeed_selenium': SeleniumIndeedScraper(user_preferences),
            'python_jobs': PythonJobsScraper(user_preferences),
            'wellfound': WellfoundScraper(user_preferences),
        }
        
        logger.info(f"Initialized {len(self.scrapers)} job scrapers")
    
    def scrape_all_sources(self, max_jobs_per_source: int = 50) -> List[Dict]:
        """
        Scrape jobs from all sources
        
        Args:
            max_jobs_per_source: Maximum jobs to get from each source
            
        Returns:
            Combined list of jobs from all sources
        """
        all_jobs = []
        
        for source_name, scraper in self.scrapers.items():
            try:
                logger.info(f"Scraping from {source_name}...")
                
                # Get search terms and locations from scraper methods
                search_terms = scraper.get_search_terms()
                locations = scraper.get_locations()
                
                # Scrape jobs from this source
                source_jobs = scraper.scrape_jobs(search_terms, locations[0] if locations else 'Remote')
                
                # Limit jobs per source
                source_jobs = source_jobs[:max_jobs_per_source]
                
                logger.info(f"Got {len(source_jobs)} jobs from {source_name}")
                all_jobs.extend(source_jobs)
                
            except Exception as e:
                logger.error(f"Error scraping from {source_name}: {e}")
                continue
        
        # Remove duplicates based on similar titles and companies
        unique_jobs = self._deduplicate_jobs(all_jobs)
        
        logger.info(f"Total unique jobs collected: {len(unique_jobs)}")
        return unique_jobs
    
    def scrape_priority_sources(self) -> List[Dict]:
        """
        Scrape from priority sources for reliable results
        Focus on sources that typically have good data quality
        """
        priority_scrapers = ['remoteok', 'python_jobs', 'indeed_selenium']
        all_jobs = []
        
        for source_name in priority_scrapers:
            if source_name not in self.scrapers:
                continue
                
            try:
                scraper = self.scrapers[source_name]
                logger.info(f"Scraping priority source: {source_name}")
                
                search_terms = scraper.get_search_terms()
                source_jobs = scraper.scrape_jobs(search_terms[:2])  # Limit search terms
                
                # Limit to top 30 jobs per source
                source_jobs = source_jobs[:30]
                
                logger.info(f"Got {len(source_jobs)} jobs from {source_name}")
                all_jobs.extend(source_jobs)
                
            except Exception as e:
                logger.error(f"Error scraping priority source {source_name}: {e}")
                continue
        
        unique_jobs = self._deduplicate_jobs(all_jobs)
        logger.info(f"Total unique jobs from priority sources: {len(unique_jobs)}")
        return unique_jobs
    
    def scrape_targeted_search(self, specific_terms: List[str], max_results: int = 100) -> List[Dict]:
        """
        Perform targeted search across all sources
        
        Args:
            specific_terms: Specific search terms to use
            max_results: Maximum total results to return
            
        Returns:
            List of jobs matching the specific terms
        """
        all_jobs = []
        
        for source_name, scraper in self.scrapers.items():
            try:
                logger.info(f"Targeted search in {source_name} for: {specific_terms}")
                source_jobs = scraper.scrape_jobs(specific_terms)
                
                # Filter for quality
                quality_jobs = self._filter_quality_jobs(source_jobs)
                all_jobs.extend(quality_jobs)
                
            except Exception as e:
                logger.error(f"Error in targeted search for {source_name}: {e}")
                continue
        
        unique_jobs = self._deduplicate_jobs(all_jobs)
        return unique_jobs[:max_results]
    
    def _deduplicate_jobs(self, jobs: List[Dict]) -> List[Dict]:
        """Remove duplicate jobs based on title, company, and location similarity"""
        if not jobs:
            return []
        
        unique_jobs = []
        seen_combinations = set()
        
        for job in jobs:
            # Create a key for deduplication
            title = job.get('title', '').lower().strip()
            company = job.get('company', '').lower().strip()
            location = job.get('location', '').lower().strip()
            
            # Clean and normalize
            title_words = set(title.split()[:3])  # First 3 words of title
            key = f"{title_words}_{company}_{location}"
            
            if key not in seen_combinations:
                seen_combinations.add(key)
                unique_jobs.append(job)
        
        return unique_jobs
    
    def _filter_quality_jobs(self, jobs: List[Dict]) -> List[Dict]:
        """Filter jobs for basic quality criteria"""
        quality_jobs = []
        
        for job in jobs:
            # Must have basic required fields
            if not job.get('title') or not job.get('company'):
                continue
            
            # Must have a valid source URL
            if not job.get('source_url') or job.get('source_url') == 'https://example.com/job':
                continue
            
            # Skip jobs with placeholder data
            if 'example.com' in job.get('source_url', ''):
                continue
            
            # Check if job matches user preferences
            if self.user_preferences and not self._matches_user_preferences(job):
                continue
            
            quality_jobs.append(job)
        
        return quality_jobs
    
    def _matches_user_preferences(self, job: Dict) -> bool:
        """Check if job matches user preferences"""
        if not self.user_preferences:
            return True
        
        # Check salary range
        job_min_salary = job.get('salary_min', 0)
        if job_min_salary and job_min_salary > (self.user_preferences.max_salary * 1.2):  # 20% tolerance
            return False
        
        # Check location preferences
        job_location = job.get('location', '').lower()
        preferred_locations = [loc.lower() for loc in self.user_preferences.preferred_locations]
        
        if preferred_locations:
            location_match = any(pref in job_location for pref in preferred_locations)
            if not location_match and 'remote' not in job_location and 'remote' not in preferred_locations:
                return False
        
        return True
    
    def get_source_stats(self) -> Dict[str, str]:
        """Get statistics about available sources"""
        stats = {}
        for source_name, scraper in self.scrapers.items():
            try:
                # Test connectivity with minimal scraping
                test_jobs = scraper.scrape_jobs(['python'], 'Remote')[:1]
                stats[source_name] = f"Active ({len(test_jobs)} test results)"
            except Exception as e:
                stats[source_name] = f"Error: {str(e)[:50]}..."
        
        return stats