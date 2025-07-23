"""
Reed.co.uk API Scraper - UK-focused job listings
Free tier: 100 API calls per month
High-quality job data with salary information
"""

import requests
from datetime import datetime, timezone, timedelta
from typing import List, Dict
import logging
from django.conf import settings
from .base_scraper import BaseScraper

logger = logging.getLogger('jobs')


class ReedAPIScraper(BaseScraper):
    """Professional API-based job scraper using Reed.co.uk (UK jobs)"""
    
    def __init__(self, user_preferences=None):
        super().__init__(user_preferences)
        self.api_key = getattr(settings, 'REED_API_KEY', 'demo_api_key')
        self.base_url = "https://www.reed.co.uk/api/1.0/search"
        self.headers = {
            'User-Agent': 'JobFinder-Pro/1.0'
        }
    
    def scrape_jobs(self, search_terms: List[str] = None, location: str = None) -> List[Dict]:
        """
        Fetch jobs from Reed API (UK job board)
        Returns high-quality UK job data with salary info
        """
        jobs = []
        
        if not search_terms:
            search_terms = self.get_search_terms()
        
        if not location:
            locations = self.get_locations()
        else:
            locations = [location]
        
        logger.info(f"Reed API: Searching for {search_terms} in {locations}")
        
        try:
            # Reed allows complex searches with good UK coverage
            for search_term in search_terms[:6]:  # Limit to preserve API calls
                for loc in locations[:3]:  # Limit locations
                    job_batch = self._search_reed_api(search_term, loc)
                    jobs.extend(job_batch)
            
            # Deduplicate by job ID
            unique_jobs = self._deduplicate_jobs(jobs)
            
            logger.info(f"Reed API: Found {len(unique_jobs)} unique jobs")
            return unique_jobs
            
        except Exception as e:
            logger.error(f"Reed API error: {e}")
            return []
    
    def _search_reed_api(self, search_term: str, location: str) -> List[Dict]:
        """Search Reed API for jobs"""
        try:
            # Map location names for UK targeting
            uk_location = self._map_location_to_uk(location)
            
            params = {
                'keywords': search_term,
                'locationName': uk_location,
                'distanceFromLocation': 15,  # 15 mile radius
                'resultsToTake': 25,  # Max results per call
                'fullTime': 'true',
                'partTime': 'false',
                'contract': 'true',
                'permanent': 'true'
            }
            
            # Reed uses basic auth with API key as username
            auth = (self.api_key, '')
            
            response = requests.get(
                self.base_url,
                params=params,
                auth=auth,
                headers=self.headers,
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                jobs = []
                
                for job_data in data.get('results', []):
                    try:
                        job = self._parse_reed_job(job_data, search_term)
                        if job:
                            jobs.append(job)
                    except Exception as e:
                        logger.warning(f"Error parsing Reed job: {e}")
                        continue
                
                logger.info(f"Reed: '{search_term}' in '{uk_location}' → {len(jobs)} jobs")
                return jobs
            else:
                logger.warning(f"Reed API returned {response.status_code}: {response.text}")
                return []
                
        except requests.RequestException as e:
            logger.error(f"Reed API request failed: {e}")
            return []
        except Exception as e:
            logger.error(f"Reed API search error: {e}")
            return []
    
    def _parse_reed_job(self, job_data: dict, search_term: str) -> Dict:
        """Parse job data from Reed API"""
        try:
            # Extract basic job info
            job_id = job_data.get('jobId', '')
            title = job_data.get('jobTitle', '').strip()
            company = job_data.get('employerName', '').strip()
            location = job_data.get('locationName', '').strip()
            description = job_data.get('jobDescription', '').strip()
            
            if not title or not company:
                return None
            
            # Handle salary information (Reed provides good salary data)
            salary_min = job_data.get('minimumSalary')
            salary_max = job_data.get('maximumSalary')
            
            # Convert annual salary to reasonable ranges
            if salary_min and salary_min > 1000:
                salary_min = int(salary_min)
            if salary_max and salary_max > 1000:
                salary_max = int(salary_max)
            
            # Determine experience level from title and description
            experience_level = self._determine_experience_level(title, description)
            
            # Extract skills from description
            skills = self.extract_skills_from_text(description)
            
            # Build job URL
            job_url = f"https://www.reed.co.uk/jobs/{job_id}"
            
            # Determine location type
            location_type = 'remote' if 'remote' in location.lower() else 'onsite'
            if 'hybrid' in description.lower():
                location_type = 'hybrid'
            
            return {
                'title': title,
                'company': company,
                'description': description,
                'location': location,
                'location_type': location_type,
                'source': 'reed',
                'source_url': job_url,
                'salary_min': salary_min,
                'salary_max': salary_max,
                'experience_level': experience_level,
                'job_type': 'full_time',
                'skills': skills,
                'posted_date': datetime.now(timezone.utc),
                'search_term': search_term
            }
            
        except Exception as e:
            logger.error(f"Error parsing Reed job: {e}")
            return None
    
    def _map_location_to_uk(self, location: str) -> str:
        """Map generic locations to UK-specific locations"""
        location_lower = location.lower()
        
        # Map common US locations to UK equivalents for Reed
        location_mapping = {
            'new york': 'London',
            'nyc': 'London', 
            'manhattan': 'London',
            'brooklyn': 'London',
            'remote': 'London',  # Reed will find remote jobs anyway
            'usa': 'London',
            'united states': 'London'
        }
        
        # Return mapped location or original if UK location
        return location_mapping.get(location_lower, location)
    
    def _determine_experience_level(self, title: str, description: str) -> str:
        """Determine experience level from job title and description"""
        title_lower = title.lower()
        desc_lower = description.lower()
        
        # Check for junior/entry level indicators
        junior_indicators = [
            'junior', 'entry level', 'graduate', 'trainee', 
            'apprentice', 'intern', 'new grad', 'associate'
        ]
        
        # Check for senior level indicators  
        senior_indicators = [
            'senior', 'lead', 'principal', 'architect', 
            'head of', 'director', 'manager', 'expert'
        ]
        
        for indicator in junior_indicators:
            if indicator in title_lower or indicator in desc_lower:
                return 'entry'
        
        for indicator in senior_indicators:
            if indicator in title_lower:
                return 'senior'
        
        return 'mid'
    
    def _deduplicate_jobs(self, jobs: List[Dict]) -> List[Dict]:
        """Remove duplicate jobs based on title and company"""
        unique_jobs = []
        seen_combinations = set()
        
        for job in jobs:
            # Create a key for deduplication
            title = job.get('title', '').lower().strip()
            company = job.get('company', '').lower().strip()
            location = job.get('location', '').lower().strip()
            
            key = f"{title}_{company}_{location}"
            
            if key not in seen_combinations and title and company:
                seen_combinations.add(key)
                unique_jobs.append(job)
        
        return unique_jobs
    
    def get_search_terms(self) -> List[str]:
        """Get enhanced search terms optimized for UK job market"""
        base_terms = super().get_search_terms() if hasattr(super(), 'get_search_terms') else []
        
        # Add UK-specific job terms
        uk_terms = [
            'Python Developer London',
            'Django Developer UK', 
            'Software Engineer London',
            'Web Developer London',
            'Full Stack Developer UK',
            'Backend Developer London',
            'Junior Developer London',
            'Graduate Developer UK'
        ]
        
        return list(set(base_terms + uk_terms))
    
    def get_locations(self) -> List[str]:
        """Get UK-focused locations for Reed API"""
        return [
            'London',
            'Manchester', 
            'Birmingham',
            'Edinburgh',
            'Bristol',
            'Leeds',
            'Remote'
        ] 