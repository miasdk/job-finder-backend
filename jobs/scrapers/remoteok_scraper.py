"""
RemoteOK job scraper for real remote job listings.
RemoteOK is scraping-friendly and provides JSON API endpoints.
"""

import requests
import json
from datetime import datetime, timezone
from typing import List, Dict, Optional
from .base_scraper import BaseScraper


class RemoteOKScraper(BaseScraper):
    """Scraper for RemoteOK remote job listings"""
    
    def __init__(self):
        super().__init__()
        self.base_url = "https://remoteok.io/api"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
            'Accept': 'application/json',
        }
    
    def scrape_jobs(self, search_terms: List[str] = None, location: str = None) -> List[Dict]:
        """
        Scrape jobs from RemoteOK API
        
        Args:
            search_terms: List of search terms (e.g., ['python', 'django'])
            location: Location filter (not used for RemoteOK since all jobs are remote)
        
        Returns:
            List of job dictionaries
        """
        jobs = []
        
        if not search_terms:
            search_terms = ['python', 'django', 'backend', 'fullstack']
        
        try:
            # RemoteOK API returns all jobs, we'll filter locally
            response = requests.get(self.base_url, headers=self.headers, timeout=30)
            response.raise_for_status()
            
            # Skip first element which is metadata
            all_jobs = response.json()[1:] if response.json() else []
            
            for job_data in all_jobs:
                # Filter jobs by search terms
                if self._matches_search_terms(job_data, search_terms):
                    processed_job = self._process_job_data(job_data)
                    if processed_job:
                        jobs.append(processed_job)
            
            print(f"RemoteOK: Found {len(jobs)} matching jobs")
            return jobs
            
        except requests.RequestException as e:
            print(f"Error scraping RemoteOK: {e}")
            return []
        except Exception as e:
            print(f"Unexpected error in RemoteOK scraper: {e}")
            return []
    
    def _matches_search_terms(self, job_data: Dict, search_terms: List[str]) -> bool:
        """Check if job matches any of the search terms"""
        if not job_data:
            return False
        
        # Combine searchable text
        searchable_text = " ".join([
            job_data.get('position', ''),
            job_data.get('description', ''),
            job_data.get('company', ''),
            " ".join(job_data.get('tags', []))
        ]).lower()
        
        # Check if any search term matches
        return any(term.lower() in searchable_text for term in search_terms)
    
    def _process_job_data(self, job_data: Dict) -> Dict:
        """Process raw RemoteOK job data into standardized format"""
        try:
            # Extract salary information
            salary_min, salary_max = self._extract_salary(job_data)
            
            # Extract skills from tags
            skills = self._extract_skills(job_data.get('tags', []))
            
            # Determine experience level
            experience_level = self._determine_experience_level(
                job_data.get('position', ''),
                job_data.get('description', '')
            )
            
            # Convert timestamp to datetime
            posted_date = self._parse_date(job_data.get('date'))
            
            processed_job = {
                'title': job_data.get('position', '').strip(),
                'company': job_data.get('company', '').strip(),
                'description': job_data.get('description', '').strip(),
                'location': 'Remote',  # All RemoteOK jobs are remote
                'location_type': 'remote',
                'salary_min': salary_min,
                'salary_max': salary_max,
                'salary_currency': 'USD',  # RemoteOK primarily uses USD
                'experience_level': experience_level,
                'job_type': 'full_time',  # Most RemoteOK jobs are full-time
                'skills': skills,
                'posted_date': posted_date,
                'source_url': f"https://remoteok.io/remote-jobs/{job_data.get('id', '')}",
                'source': 'RemoteOK',
                'external_id': str(job_data.get('id', '')),
                'raw_data': job_data
            }
            
            return processed_job
            
        except Exception as e:
            print(f"Error processing RemoteOK job data: {e}")
            return None
    
    def _extract_salary(self, job_data: Dict) -> tuple:
        """Extract salary range from job data"""
        salary_min = job_data.get('salary_min')
        salary_max = job_data.get('salary_max')
        
        # Convert to integers if they exist and are valid
        try:
            if salary_min:
                salary_min = int(salary_min)
            if salary_max:
                salary_max = int(salary_max)
        except (ValueError, TypeError):
            salary_min = salary_max = None
        
        return salary_min, salary_max
    
    def _extract_skills(self, tags: List[str]) -> List[str]:
        """Extract relevant skills from job tags"""
        if not tags:
            return []
        
        # Common tech skills to look for
        relevant_skills = {
            'python', 'django', 'flask', 'fastapi', 'javascript', 'typescript',
            'react', 'vue', 'angular', 'nodejs', 'postgresql', 'mysql', 'redis',
            'mongodb', 'aws', 'docker', 'kubernetes', 'git', 'linux', 'sql',
            'html', 'css', 'restapi', 'graphql', 'tensorflow', 'pytorch',
            'machine learning', 'data science', 'api', 'backend', 'frontend',
            'fullstack', 'devops'
        }
        
        skills = []
        for tag in tags:
            tag_lower = tag.lower().replace('-', ' ').replace('_', ' ')
            if tag_lower in relevant_skills:
                skills.append(tag)
        
        return skills
    
    def _determine_experience_level(self, title: str, description: str) -> str:
        """Determine experience level from job title and description"""
        text = f"{title} {description}".lower()
        
        if any(term in text for term in ['senior', 'sr.', 'lead', 'principal', 'staff']):
            return 'senior'
        elif any(term in text for term in ['junior', 'jr.', 'entry', 'entry-level', 'new grad']):
            return 'entry'
        else:
            return 'mid'
    
    def _parse_date(self, date_str) -> datetime:
        """Parse RemoteOK date format"""
        if not date_str:
            return datetime.now(timezone.utc)
        
        try:
            # RemoteOK uses Unix timestamp
            if isinstance(date_str, (int, float)):
                return datetime.fromtimestamp(date_str, tz=timezone.utc)
            elif isinstance(date_str, str) and date_str.isdigit():
                return datetime.fromtimestamp(int(date_str), tz=timezone.utc)
        except (ValueError, OSError):
            pass
        
        return datetime.now(timezone.utc)