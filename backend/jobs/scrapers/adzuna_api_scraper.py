"""
Adzuna Jobs API Scraper - Free tier: 1000 calls/month
High-quality job data from major aggregator
"""

import requests
from datetime import datetime, timezone, timedelta
from typing import List, Dict
import logging
from django.conf import settings
from .base_scraper import BaseScraper

logger = logging.getLogger('jobs')


class AdzunaAPIScraper(BaseScraper):
    """Professional API-based job scraper using Adzuna's job aggregation service"""
    
    def __init__(self, user_preferences=None):
        super().__init__(user_preferences)
        self.app_id = getattr(settings, 'ADZUNA_APP_ID', 'demo_app_id')
        self.api_key = getattr(settings, 'ADZUNA_API_KEY', 'demo_api_key')
        self.base_url = "https://api.adzuna.com/v1/api/jobs/us/search"
        self.headers = {
            'User-Agent': 'JobFinder-Pro/1.0'
        }
    
    def scrape_jobs(self, search_terms: List[str] = None, location: str = None) -> List[Dict]:
        """
        Fetch jobs from Adzuna API
        Returns professional job data with salary info, company details
        """
        jobs = []
        
        if not search_terms:
            search_terms = self.get_search_terms()
        
        if not location:
            locations = self.get_locations()
        else:
            locations = [location]
        
        logger.info(f"Adzuna API: Searching for {search_terms} in {locations}")
        
        try:
            # Adzuna allows complex searches
            for search_term in search_terms[:3]:  # Limit to preserve API calls
                for loc in locations[:2]:
                    job_batch = self._search_adzuna_api(search_term, loc)
                    jobs.extend(job_batch)
            
            # Deduplicate by company + title
            unique_jobs = self._deduplicate_jobs(jobs)
            
            logger.info(f"Adzuna API: Found {len(unique_jobs)} unique jobs")
            return unique_jobs
            
        except Exception as e:
            logger.error(f"Adzuna API error: {e}")
            return []
    
    def _search_adzuna_api(self, search_term: str, location: str) -> List[Dict]:
        """Make API call to Adzuna"""
        
        params = {
            'app_id': self.app_id,
            'app_key': self.api_key,
            'what': search_term,
            'where': location,
            'results_per_page': 20,
            'sort_by': 'date',
            'content-type': 'application/json'
        }
        
        try:
            response = requests.get(self.base_url, params=params, headers=self.headers, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            jobs = []
            
            for job_data in data.get('results', []):
                processed_job = self._process_adzuna_job(job_data)
                if processed_job:
                    jobs.append(processed_job)
            
            logger.info(f"Adzuna: {len(jobs)} jobs for '{search_term}' in '{location}'")
            return jobs
            
        except requests.RequestException as e:
            logger.error(f"Adzuna API request failed: {e}")
            return []
        except Exception as e:
            logger.error(f"Adzuna processing error: {e}")
            return []
    
    def _process_adzuna_job(self, job_data: Dict) -> Dict:
        """Convert Adzuna API response to our job format"""
        try:
            # Extract salary info (Adzuna provides good salary data)
            salary_min = job_data.get('salary_min')
            salary_max = job_data.get('salary_max')
            
            # Adzuna provides rich location data
            location_info = job_data.get('location', {})
            location = f"{location_info.get('display_name', 'Unknown')}"
            
            # Category mapping for better job classification
            category = job_data.get('category', {}).get('label', 'Technology')
            
            # Extract company info
            company_name = job_data.get('company', {}).get('display_name', 'Unknown Company')
            
            # Determine location type from description
            description = job_data.get('description', '')
            location_type = self.determine_location_type('', description, location)
            
            # Extract skills from description
            skills = self.extract_skills_from_text(f"{job_data.get('title', '')} {description}")
            
            # Determine experience level
            title = job_data.get('title', '')
            experience_level = self.determine_experience_level(title, description)
            
            return {
                'title': title,
                'company': company_name,
                'description': description,
                'location': location,
                'location_type': location_type,
                'salary_min': int(salary_min) if salary_min else None,
                'salary_max': int(salary_max) if salary_max else None,
                'salary_currency': 'USD',
                'experience_level': experience_level,
                'job_type': 'full_time',
                'skills': skills,
                'posted_date': self._parse_date(job_data.get('created')),
                'source_url': job_data.get('redirect_url', ''),
                'source': 'Adzuna',
                'external_id': job_data.get('id', ''),
                'raw_data': {
                    'category': category,
                    'contract_time': job_data.get('contract_time'),
                    'company_id': job_data.get('company', {}).get('id'),
                }
            }
            
        except Exception as e:
            logger.error(f"Error processing Adzuna job: {e}")
            return None
    
    def _parse_date(self, date_str: str) -> datetime:
        """Parse Adzuna date format"""
        try:
            if date_str:
                # Adzuna uses ISO format: 2025-01-23T10:30:00Z
                return datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        except:
            pass
        return datetime.now(timezone.utc)
    
    def _deduplicate_jobs(self, jobs: List[Dict]) -> List[Dict]:
        """Remove duplicates based on company + title similarity"""
        unique_jobs = []
        seen_combinations = set()
        
        for job in jobs:
            # Create dedup key
            title_key = job.get('title', '').lower().strip()[:50]
            company_key = job.get('company', '').lower().strip()[:30]
            key = f"{title_key}_{company_key}"
            
            if key not in seen_combinations:
                seen_combinations.add(key)
                unique_jobs.append(job)
        
        return unique_jobs