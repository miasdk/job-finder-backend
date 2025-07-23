"""
Enhanced Indeed scraper using their JSON API endpoints
"""

import requests
import json
from datetime import datetime, timezone
from typing import List, Dict, Optional
from urllib.parse import urlencode, quote_plus
from .base_scraper import BaseScraper


class EnhancedIndeedScraper(BaseScraper):
    """Enhanced scraper for Indeed job listings using their API endpoints"""
    
    def __init__(self, user_preferences=None):
        super().__init__(user_preferences)
        self.base_url = "https://www.indeed.com/jobs"
        self.api_url = "https://www.indeed.com/api/offers"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Referer': 'https://www.indeed.com/',
            'Origin': 'https://www.indeed.com'
        }
    
    def scrape_jobs(self, search_terms: List[str] = None, location: str = None) -> List[Dict]:
        """
        Scrape jobs from Indeed using their search results
        
        Args:
            search_terms: List of search terms (e.g., ['python', 'django'])
            location: Location filter (e.g., 'New York, NY', 'Remote')
        
        Returns:
            List of job dictionaries
        """
        jobs = []
        
        if not search_terms:
            search_terms = self.get_search_terms()
        
        if not location:
            locations = self.get_locations()
        else:
            locations = [location]
        
        print(f"Indeed: Scraping for {search_terms} in {locations}")
        
        for search_term in search_terms[:2]:  # Limit to avoid rate limiting
            for loc in locations[:2]:  # Limit locations
                try:
                    jobs_batch = self._scrape_for_term_and_location(search_term, loc)
                    jobs.extend(jobs_batch)
                except Exception as e:
                    print(f"Error scraping Indeed for {search_term} in {loc}: {e}")
                    continue
        
        # Remove duplicates by source_url
        seen_urls = set()
        unique_jobs = []
        for job in jobs:
            if job.get('source_url') not in seen_urls:
                seen_urls.add(job.get('source_url'))
                unique_jobs.append(job)
        
        print(f"Indeed: Found {len(unique_jobs)} unique jobs")
        return unique_jobs
    
    def _scrape_for_term_and_location(self, search_term: str, location: str) -> List[Dict]:
        """Scrape jobs for a specific search term and location"""
        params = {
            'q': search_term,
            'l': location,
            'sort': 'date',
            'radius': '25',
            'limit': '20',
            'fromage': '14'  # Last 14 days
        }
        
        # Build search URL
        search_url = f"{self.base_url}?{urlencode(params)}"
        
        try:
            response = requests.get(search_url, headers=self.headers, timeout=15)
            response.raise_for_status()
            
            # Extract job data from HTML
            jobs = self._extract_jobs_from_html(response.text, search_term, location)
            return jobs
            
        except requests.RequestException as e:
            print(f"Request error for Indeed search: {e}")
            return []
        except Exception as e:
            print(f"Unexpected error in Indeed scraper: {e}")
            return []
    
    def _extract_jobs_from_html(self, html: str, search_term: str, location: str) -> List[Dict]:
        """Extract job information from Indeed HTML response"""
        from bs4 import BeautifulSoup
        
        soup = BeautifulSoup(html, 'html.parser')
        jobs = []
        
        # Find job cards in Indeed's HTML structure
        job_elements = soup.find_all('div', class_=['job_seen_beacon', 'slider_container'])
        
        for job_element in job_elements:
            try:
                job_data = self._extract_job_info(job_element)
                if job_data and self._is_relevant_job(job_data, search_term):
                    jobs.append(job_data)
            except Exception as e:
                print(f"Error extracting job info: {e}")
                continue
        
        return jobs
    
    def _extract_job_info(self, job_element) -> Optional[Dict]:
        """Extract job information from a job HTML element"""
        try:
            # Extract title and link
            title_link = job_element.find('h2', class_='jobTitle') or job_element.find('a', {'data-jk': True})
            if not title_link:
                return None
            
            title = title_link.get_text(strip=True)
            job_key = title_link.get('data-jk') or ''
            job_url = f"https://www.indeed.com/viewjob?jk={job_key}" if job_key else ''
            
            # Extract company
            company_elem = job_element.find('span', class_='companyName') or job_element.find('a', {'data-testid': 'company-name'})
            company = company_elem.get_text(strip=True) if company_elem else 'Unknown Company'
            
            # Extract location
            location_elem = job_element.find('div', class_='companyLocation') or job_element.find('div', {'data-testid': 'job-location'})
            location = location_elem.get_text(strip=True) if location_elem else 'Not specified'
            
            # Extract salary if available
            salary_elem = job_element.find('span', class_='estimated-salary') or job_element.find('span', class_='salary-snippet')
            salary_text = salary_elem.get_text(strip=True) if salary_elem else ''
            salary_min, salary_max = self._parse_salary(salary_text)
            
            # Extract snippet/description
            snippet_elem = job_element.find('div', class_='summary') or job_element.find('div', class_='job-snippet')
            description = snippet_elem.get_text(strip=True) if snippet_elem else ''
            
            # Extract skills from description
            skills = self.extract_skills_from_text(f"{title} {description}")
            
            # Determine location type
            location_type = self._determine_location_type(location, description)
            
            # Determine experience level
            experience_level = self._determine_experience_level(title, description)
            
            return {
                'title': title,
                'company': company,
                'description': description,
                'location': location,
                'location_type': location_type,
                'salary_min': salary_min,
                'salary_max': salary_max,
                'salary_currency': 'USD',
                'experience_level': experience_level,
                'job_type': 'full_time',
                'skills': skills,
                'posted_date': datetime.now(timezone.utc),  # Indeed doesn't always show exact dates
                'source_url': job_url,
                'source': 'Indeed',
                'external_id': job_key,
            }
            
        except Exception as e:
            print(f"Error extracting individual job info: {e}")
            return None
    
    def _parse_salary(self, salary_text: str) -> tuple:
        """Parse salary information from text"""
        if not salary_text:
            return None, None
        
        import re
        
        # Remove common prefixes and clean
        salary_text = salary_text.replace('$', '').replace(',', '').lower()
        
        # Look for ranges like "80000 - 120000" or "80k - 120k"
        range_match = re.search(r'(\d+)k?\s*-\s*(\d+)k?', salary_text)
        if range_match:
            min_sal = int(range_match.group(1))
            max_sal = int(range_match.group(2))
            
            # Convert k values
            if 'k' in salary_text or min_sal < 1000:
                min_sal *= 1000
                max_sal *= 1000
            
            return min_sal, max_sal
        
        # Look for single values
        single_match = re.search(r'(\d+)k?', salary_text)
        if single_match:
            salary = int(single_match.group(1))
            if 'k' in salary_text or salary < 1000:
                salary *= 1000
            return salary, None
        
        return None, None
    
    def _determine_location_type(self, location: str, description: str) -> str:
        """Determine if job is remote, hybrid, or onsite"""
        text_lower = f"{location} {description}".lower()
        
        if any(keyword in text_lower for keyword in ['remote', 'work from home', 'telecommute', 'distributed']):
            return 'remote'
        elif any(keyword in text_lower for keyword in ['hybrid', 'flexible location']):
            return 'hybrid'
        else:
            return 'onsite'
    
    def _determine_experience_level(self, title: str, description: str) -> str:
        """Determine experience level from title and description"""
        text_lower = f"{title} {description}".lower()
        
        if any(keyword in text_lower for keyword in ['entry level', 'junior', 'graduate', 'new grad', 'associate']):
            return 'entry'
        elif any(keyword in text_lower for keyword in ['senior', 'lead', 'principal', 'staff']):
            return 'senior'
        elif any(keyword in text_lower for keyword in ['mid level', 'intermediate', 'experienced']):
            return 'mid'
        else:
            return 'junior'  # Default for undefined levels
    
    def _is_relevant_job(self, job_data: Dict, search_term: str) -> bool:
        """Check if job is relevant to our search criteria"""
        if not job_data:
            return False
        
        # Basic relevance check
        title_desc = f"{job_data.get('title', '')} {job_data.get('description', '')}".lower()
        
        # Must contain at least one of our target keywords
        relevant_keywords = ['python', 'django', 'backend', 'full stack', 'software engineer', 'developer']
        
        if not any(keyword in title_desc for keyword in relevant_keywords):
            return False
        
        # Check if it matches user preferences
        if self.user_preferences:
            # Check salary range if specified
            min_salary = job_data.get('salary_min', 0) or 0
            if min_salary > 0 and min_salary < (self.user_preferences.min_salary * 0.7):  # 30% tolerance
                return False
        
        return True