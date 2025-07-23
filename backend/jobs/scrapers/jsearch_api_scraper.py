"""
JSearch API Scraper - RapidAPI service for Google for Jobs data
Free tier: 2500 requests/month
High-quality job data aggregated from Google for Jobs, Indeed, LinkedIn
"""

import requests
from datetime import datetime, timezone, timedelta
from typing import List, Dict
import logging
from django.conf import settings
from .base_scraper import BaseScraper

logger = logging.getLogger('jobs')


class JSearchAPIScraper(BaseScraper):
    """Professional API-based job scraper using JSearch (Google for Jobs data)"""
    
    def __init__(self, user_preferences=None):
        super().__init__(user_preferences)
        self.api_key = getattr(settings, 'JSEARCH_API_KEY', 'demo_api_key')
        self.base_url = "https://jsearch.p.rapidapi.com/search"
        self.headers = {
            'X-RapidAPI-Key': self.api_key,
            'X-RapidAPI-Host': 'jsearch.p.rapidapi.com',
            'User-Agent': 'JobFinder-Pro/1.0'
        }
    
    def scrape_jobs(self, search_terms: List[str] = None, location: str = None) -> List[Dict]:
        """
        Fetch jobs from JSearch API (Google for Jobs data)
        Returns high-quality job data with company details and apply links
        """
        jobs = []
        
        if not search_terms:
            search_terms = self.get_search_terms()
        
        if not location:
            locations = self.get_locations()
        else:
            locations = [location]
        
        logger.info(f"JSearch API: Searching for {search_terms} in {locations}")
        
        try:
            # JSearch allows complex searches
            for search_term in search_terms[:4]:  # Limit to preserve API calls
                for loc in locations[:3]:  # Limit locations
                    job_batch = self._search_jsearch_api(search_term, loc)
                    jobs.extend(job_batch)
            
            # Deduplicate by job ID
            unique_jobs = self._deduplicate_jobs(jobs)
            
            logger.info(f"JSearch API: Found {len(unique_jobs)} unique jobs")
            return unique_jobs
            
        except Exception as e:
            logger.error(f"JSearch API error: {e}")
            return []
    
    def _search_jsearch_api(self, search_term: str, location: str) -> List[Dict]:
        """Make API call to JSearch"""
        
        params = {
            'query': f"{search_term} in {location}",
            'page': '1',
            'num_pages': '1',
            'date_posted': 'week',  # Recent jobs only
            'employment_types': 'FULLTIME,PARTTIME,CONTRACTOR',
            'job_requirements': 'under_3_years_experience,more_than_3_years_experience',
            'country': 'us'
        }
        
        try:
            response = requests.get(self.base_url, headers=self.headers, params=params, timeout=30)
            
            if response.status_code == 401:
                logger.error("JSearch API: 401 Unauthorized - check API key")
                return []
            
            response.raise_for_status()
            data = response.json()
            
            jobs = []
            
            for job_data in data.get('data', []):
                processed_job = self._process_jsearch_job(job_data)
                if processed_job:
                    jobs.append(processed_job)
            
            logger.info(f"JSearch: {len(jobs)} jobs for '{search_term}' in '{location}'")
            return jobs
            
        except requests.RequestException as e:
            logger.error(f"JSearch API request failed: {e}")
            return []
        except Exception as e:
            logger.error(f"JSearch processing error: {e}")
            return []
    
    def _process_jsearch_job(self, job_data: Dict) -> Dict:
        """Convert JSearch API response to our job format"""
        try:
            # JSearch provides rich job data from Google for Jobs
            
            # Extract salary info (JSearch often has good salary data)
            salary_min = None
            salary_max = None
            
            if job_data.get('job_salary_period') and job_data.get('job_min_salary'):
                salary_min = job_data.get('job_min_salary')
                salary_max = job_data.get('job_max_salary', salary_min)
                
                # Convert to annual if needed
                if job_data.get('job_salary_period') == 'HOUR':
                    salary_min = salary_min * 40 * 52 if salary_min else None
                    salary_max = salary_max * 40 * 52 if salary_max else None
            
            # Extract location and determine type
            location = job_data.get('job_city') or 'Unknown'
            if job_data.get('job_state'):
                location = f"{location}, {job_data.get('job_state')}"
            
            # Determine location type from job data
            description = job_data.get('job_description') or ''
            job_title = job_data.get('job_title') or ''
            location_type = self.determine_location_type(job_title, description, location)
            
            # Extract skills from description
            skills = self.extract_skills_from_text(f"{job_title} {description}")
            
            # Determine experience level
            experience_level = self.determine_experience_level(job_title, description)
            
            # Employment type mapping
            employment_type_map = {
                'FULLTIME': 'full_time',
                'PARTTIME': 'part_time', 
                'CONTRACTOR': 'contract',
                'INTERN': 'internship'
            }
            employment_type = employment_type_map.get(
                job_data.get('job_employment_type', 'FULLTIME'), 
                'full_time'
            )
            
            return {
                'title': job_title,
                'company': job_data.get('employer_name', 'Unknown Company'),
                'description': description,
                'location': location,
                'location_type': location_type,
                'salary_min': salary_min,
                'salary_max': salary_max,
                'salary_currency': job_data.get('job_salary_currency', 'USD'),
                'experience_level': experience_level,
                'job_type': employment_type,
                'skills': skills,
                'posted_date': self._parse_date(job_data.get('job_posted_at_datetime_utc')),
                'source_url': job_data.get('job_apply_link', ''),
                'source': 'JSearch',
                'external_id': job_data.get('job_id', ''),
                'raw_data': {
                    'job_publisher': job_data.get('job_publisher'),
                    'job_apply_quality_score': job_data.get('job_apply_quality_score'),
                    'job_benefits': job_data.get('job_benefits'),
                    'employer_company_type': job_data.get('employer_company_type'),
                    'job_required_education': job_data.get('job_required_education'),
                    'job_required_experience': job_data.get('job_required_experience'),
                }
            }
            
        except Exception as e:
            logger.error(f"Error processing JSearch job: {e}")
            return None
    
    def _parse_date(self, date_str: str) -> datetime:
        """Parse JSearch date format"""
        try:
            if date_str:
                # JSearch uses ISO format: 2025-01-23T10:30:00.000Z
                return datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        except:
            pass
        return datetime.now(timezone.utc)
    
    def _deduplicate_jobs(self, jobs: List[Dict]) -> List[Dict]:
        """Remove duplicates based on job ID and URL similarity"""
        unique_jobs = []
        seen_ids = set()
        seen_urls = set()
        
        for job in jobs:
            # Use external ID if available
            job_id = job.get('external_id', '')
            job_url = job.get('source_url', '')
            
            # Create dedup key
            if job_id and job_id not in seen_ids:
                seen_ids.add(job_id)
                unique_jobs.append(job)
            elif job_url and job_url not in seen_urls:
                seen_urls.add(job_url)
                unique_jobs.append(job)
        
        return unique_jobs