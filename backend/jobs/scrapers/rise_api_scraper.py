"""
Rise Jobs API Scraper - Tech-focused job listings
Free tier: Up to 20 jobs per request
Global tech job coverage
"""

import requests
from datetime import datetime, timezone, timedelta
from typing import List, Dict
import logging
from .base_scraper import BaseScraper

logger = logging.getLogger('jobs')


class RiseAPIScraper(BaseScraper):
    """Free API-based job scraper using Rise platform (tech jobs)"""
    
    def __init__(self, user_preferences=None):
        super().__init__(user_preferences)
        self.base_url = "https://api.joinrise.io/api/v1/jobs/public"
        self.headers = {
            'User-Agent': 'JobFinder-Pro/1.0',
            'Accept': 'application/json'
        }
    
    def scrape_jobs(self, search_terms: List[str] = None, location: str = None) -> List[Dict]:
        """
        Fetch jobs from Rise API (free tech job platform)
        Returns tech-focused job data
        """
        jobs = []
        
        if not search_terms:
            search_terms = self.get_search_terms()
        
        logger.info(f"Rise API: Searching for tech jobs")
        
        try:
            # Rise API provides tech jobs - we'll filter by our search terms
            for page in range(1, 6):  # Get first 5 pages (up to 100 jobs)
                job_batch = self._search_rise_api(page, location)
                if not job_batch:
                    break
                jobs.extend(job_batch)
            
            # Filter jobs by search terms
            filtered_jobs = self._filter_jobs_by_terms(jobs, search_terms)
            
            # Deduplicate
            unique_jobs = self._deduplicate_jobs(filtered_jobs)
            
            logger.info(f"Rise API: Found {len(unique_jobs)} unique tech jobs")
            return unique_jobs
            
        except Exception as e:
            logger.error(f"Rise API error: {e}")
            return []
    
    def _search_rise_api(self, page: int, location: str = None) -> List[Dict]:
        """Search Rise API for jobs"""
        try:
            params = {
                'page': page,
                'limit': 20,  # Max per request
                'sort': 'desc',
                'sortedBy': 'createdAt'
            }
            
            # Add location if specified
            if location and location.lower() != 'remote':
                params['jobLoc'] = location
            
            response = requests.get(
                self.base_url,
                params=params,
                headers=self.headers,
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                jobs = []
                
                job_list = data.get('data', []) if isinstance(data.get('data'), list) else data.get('jobs', [])
                
                for job_data in job_list:
                    try:
                        job = self._parse_rise_job(job_data)
                        if job:
                            jobs.append(job)
                    except Exception as e:
                        logger.warning(f"Error parsing Rise job: {e}")
                        continue
                
                logger.info(f"Rise API: Page {page} → {len(jobs)} jobs")
                return jobs
            else:
                logger.warning(f"Rise API returned {response.status_code}: {response.text}")
                return []
                
        except requests.RequestException as e:
            logger.error(f"Rise API request failed: {e}")
            return []
        except Exception as e:
            logger.error(f"Rise API search error: {e}")
            return []
    
    def _parse_rise_job(self, job_data: dict) -> Dict:
        """Parse job data from Rise API"""
        try:
            # Extract basic job info - handle different possible field names
            title = job_data.get('title') or job_data.get('jobTitle', '').strip()
            company = job_data.get('company') or job_data.get('companyName', '').strip()
            description = job_data.get('description') or job_data.get('jobDescription', '').strip()
            location = job_data.get('location') or job_data.get('jobLocation', '').strip()
            
            if not title or not company:
                return None
            
            # Handle salary information
            salary_min = None
            salary_max = None
            
            # Try different salary field names
            if 'salary' in job_data:
                salary_info = job_data['salary']
                if isinstance(salary_info, dict):
                    salary_min = salary_info.get('min') or salary_info.get('minimum')
                    salary_max = salary_info.get('max') or salary_info.get('maximum')
                elif isinstance(salary_info, str) and '$' in salary_info:
                    # Parse salary string like "$50,000 - $70,000"
                    import re
                    salary_match = re.findall(r'\$?([0-9,]+)', salary_info)
                    if len(salary_match) >= 2:
                        salary_min = int(salary_match[0].replace(',', ''))
                        salary_max = int(salary_match[1].replace(',', ''))
            
            # Determine experience level
            experience_level = self._determine_experience_level(title, description)
            
            # Extract skills from description
            skills = self.extract_skills_from_text(description)
            
            # Build job URL
            job_id = job_data.get('id') or job_data.get('jobId', '')
            job_url = job_data.get('url') or job_data.get('applyUrl') or f"https://joinrise.io/jobs/{job_id}"
            
            # Determine location type
            location_type = 'remote'
            if location:
                if 'remote' in location.lower():
                    location_type = 'remote'
                elif 'hybrid' in location.lower():
                    location_type = 'hybrid'
                else:
                    location_type = 'onsite'
            
            # Parse posted date
            posted_date = datetime.now(timezone.utc)
            if 'createdAt' in job_data or 'datePosted' in job_data:
                date_str = job_data.get('createdAt') or job_data.get('datePosted')
                if date_str:
                    try:
                        posted_date = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                    except:
                        pass
            
            return {
                'title': title,
                'company': company,
                'description': description,
                'location': location or 'Remote',
                'location_type': location_type,
                'source': 'rise',
                'source_url': job_url,
                'salary_min': salary_min,
                'salary_max': salary_max,
                'experience_level': experience_level,
                'job_type': 'full_time',
                'skills': skills,
                'posted_date': posted_date,
                'search_term': 'tech jobs'
            }
            
        except Exception as e:
            logger.error(f"Error parsing Rise job: {e}")
            return None
    
    def _filter_jobs_by_terms(self, jobs: List[Dict], search_terms: List[str]) -> List[Dict]:
        """Filter jobs by search terms since Rise API doesn't support keyword search"""
        if not search_terms:
            return jobs
        
        filtered_jobs = []
        
        for job in jobs:
            title_lower = job.get('title', '').lower()
            desc_lower = job.get('description', '').lower()
            
            # Check if any search term matches title or description
            for term in search_terms:
                term_words = term.lower().split()
                
                # Check if all words in the search term appear in title or description
                title_match = all(word in title_lower for word in term_words)
                desc_match = all(word in desc_lower for word in term_words)
                
                if title_match or desc_match:
                    job['search_term'] = term
                    filtered_jobs.append(job)
                    break
        
        return filtered_jobs
    
    def _determine_experience_level(self, title: str, description: str) -> str:
        """Determine experience level from job title and description"""
        title_lower = title.lower()
        desc_lower = description.lower()
        
        # Check for junior/entry level indicators
        junior_indicators = [
            'junior', 'entry level', 'graduate', 'trainee', 
            'apprentice', 'intern', 'new grad', 'associate', 'jr'
        ]
        
        # Check for senior level indicators  
        senior_indicators = [
            'senior', 'lead', 'principal', 'architect', 
            'head of', 'director', 'manager', 'expert', 'sr'
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
            
            key = f"{title}_{company}"
            
            if key not in seen_combinations and title and company:
                seen_combinations.add(key)
                unique_jobs.append(job)
        
        return unique_jobs
    
    def get_search_terms(self) -> List[str]:
        """Get tech-focused search terms for filtering"""
        return [
            'Python',
            'Django', 
            'JavaScript',
            'React',
            'Node.js',
            'Software Engineer',
            'Web Developer',
            'Full Stack Developer',
            'Backend Developer',
            'Frontend Developer',
            'Junior Developer',
            'Software Developer'
        ] 