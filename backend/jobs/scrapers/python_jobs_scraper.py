"""
Python.org job board scraper for Python-specific job listings.
Scrapes from the official Python.org jobs page.
"""

import requests
from bs4 import BeautifulSoup
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Optional
import re
from .base_scraper import BaseScraper


class PythonJobsScraper(BaseScraper):
    """Scraper for Python.org job board"""
    
    def __init__(self, user_preferences=None):
        super().__init__(user_preferences)
        self.base_url = "https://www.python.org/jobs"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        }
    
    def scrape_jobs(self, search_terms: List[str] = None, location: str = None) -> List[Dict]:
        """
        Scrape jobs from Python.org job board
        
        Args:
            search_terms: List of search terms (e.g., ['django', 'web'])
            location: Location filter
        
        Returns:
            List of job dictionaries
        """
        jobs = []
        
        if not search_terms:
            search_terms = ['django', 'web', 'backend', 'api', 'full stack']
        
        try:
            # Get the main jobs page
            response = requests.get(self.base_url, headers=self.headers, timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Find job listings - they're typically in a list format
            job_links = []
            
            # Look for job listing containers
            job_containers = soup.find_all(['div', 'li'], class_=re.compile(r'job|listing'))
            
            if not job_containers:
                # Fallback: look for links that seem to be job postings
                all_links = soup.find_all('a', href=True)
                for link in all_links:
                    href = link.get('href', '')
                    if '/jobs/' in href and href != '/jobs/':
                        job_links.append(href)
            else:
                # Extract links from job containers
                for container in job_containers:
                    link = container.find('a', href=True)
                    if link:
                        job_links.append(link.get('href'))
            
            # Make URLs absolute
            job_links = [
                link if link.startswith('http') else f"https://www.python.org{link}"
                for link in job_links
            ]
            
            # Remove duplicates
            job_links = list(set(job_links))
            
            print(f"Found {len(job_links)} job links on Python.org")
            
            # Scrape individual job pages
            for job_url in job_links[:20]:  # Limit to first 20 to avoid overwhelming
                job_data = self._scrape_job_detail(job_url)
                if job_data and self._matches_criteria(job_data, search_terms, location):
                    jobs.append(job_data)
            
            print(f"Python.org: Found {len(jobs)} matching jobs")
            return jobs
            
        except requests.RequestException as e:
            print(f"Error scraping Python.org jobs: {e}")
            return []
        except Exception as e:
            print(f"Unexpected error in Python.org scraper: {e}")
            return []
    
    def _scrape_job_detail(self, job_url: str) -> Dict:
        """Scrape details from individual job page"""
        try:
            response = requests.get(job_url, headers=self.headers, timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Extract job information
            title = self._extract_title(soup)
            company = self._extract_company(soup)
            description = self._extract_description(soup)
            location = self._extract_location(soup)
            posted_date = self._extract_posted_date(soup)
            
            if not title:
                return None
            
            # Determine location type
            location_type = self._determine_location_type(location, description)
            
            # Extract skills
            skills = self._extract_skills_from_text(f"{title} {description}")
            
            # Determine experience level
            experience_level = self.determine_experience_level(title, description)
            
            # Extract salary if available
            salary_min, salary_max = self._extract_salary_from_text(description)
            
            job_data = {
                'title': title,
                'company': company or 'Not specified',
                'description': description,
                'location': location or 'Not specified',
                'location_type': location_type,
                'salary_min': salary_min,
                'salary_max': salary_max,
                'salary_currency': 'USD',
                'experience_level': experience_level,
                'job_type': 'full_time',
                'skills': skills,
                'posted_date': posted_date,
                'source_url': job_url,
                'source': 'Python.org',
                'external_id': job_url.split('/')[-1] or job_url.split('/')[-2],
                'raw_data': {'url': job_url}
            }
            
            return job_data
            
        except Exception as e:
            print(f"Error scraping job detail from {job_url}: {e}")
            return None
    
    def _extract_title(self, soup: BeautifulSoup) -> str:
        """Extract job title from page"""
        # Try multiple selectors
        selectors = ['h1', '.job-title', '.title', 'title']
        
        for selector in selectors:
            element = soup.select_one(selector)
            if element:
                title = element.get_text(strip=True)
                # Clean up title
                title = re.sub(r'\s*\|\s*Python\.org.*$', '', title)
                if title and len(title) > 3:
                    return title
        
        return ""
    
    def _extract_company(self, soup: BeautifulSoup) -> str:
        """Extract company name from page"""
        # Try multiple selectors
        selectors = ['.company', '.company-name', '.employer']
        
        for selector in selectors:
            element = soup.select_one(selector)
            if element:
                return element.get_text(strip=True)
        
        # Look for "at Company" pattern in text
        text = soup.get_text()
        company_match = re.search(r'\bat\s+([A-Z][a-zA-Z\s&.,]+?)(?:\s|$)', text)
        if company_match:
            return company_match.group(1).strip()
        
        return ""
    
    def _extract_description(self, soup: BeautifulSoup) -> str:
        """Extract job description from page"""
        # Try multiple selectors
        selectors = ['.job-description', '.description', '.content', '.job-content']
        
        for selector in selectors:
            element = soup.select_one(selector)
            if element:
                return element.get_text(strip=True)
        
        # Fallback: get main content
        main_content = soup.find('main') or soup.find('body')
        if main_content:
            # Remove navigation and footer elements
            for unwanted in main_content.find_all(['nav', 'footer', 'header', 'aside']):
                unwanted.decompose()
            return main_content.get_text(strip=True)
        
        return soup.get_text(strip=True)
    
    def _extract_location(self, soup: BeautifulSoup) -> str:
        """Extract location from page"""
        # Try multiple selectors
        selectors = ['.location', '.job-location', '.address']
        
        for selector in selectors:
            element = soup.select_one(selector)
            if element:
                return element.get_text(strip=True)
        
        # Look for location patterns in text
        text = soup.get_text()
        location_patterns = [
            r'Location:\s*([^\n]+)',
            r'Based in\s+([^\n]+)',
            r'Located in\s+([^\n]+)',
            r'\b(New York|NYC|San Francisco|Austin|Seattle|Boston|Remote|Chicago|Los Angeles)\b'
        ]
        
        for pattern in location_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        
        return ""
    
    def _extract_posted_date(self, soup: BeautifulSoup) -> datetime:
        """Extract posted date from page"""
        # Try multiple selectors
        selectors = ['.date', '.posted-date', '.job-date']
        
        for selector in selectors:
            element = soup.select_one(selector)
            if element:
                date_text = element.get_text(strip=True)
                parsed_date = self._parse_date_string(date_text)
                if parsed_date:
                    return parsed_date
        
        # Look for date patterns in text
        text = soup.get_text()
        date_patterns = [
            r'Posted:\s*([^\n]+)',
            r'Date:\s*([^\n]+)',
            r'\b(\d{1,2}/\d{1,2}/\d{4})\b',
            r'\b(\w+ \d{1,2}, \d{4})\b'
        ]
        
        for pattern in date_patterns:
            match = re.search(pattern, text)
            if match:
                parsed_date = self._parse_date_string(match.group(1))
                if parsed_date:
                    return parsed_date
        
        # Default to recent date (assume jobs are recent)
        return datetime.now(timezone.utc) - timedelta(days=7)
    
    def _parse_date_string(self, date_str: str) -> datetime:
        """Parse various date string formats"""
        if not date_str:
            return datetime.now(timezone.utc)
        
        # Clean up the date string
        date_str = re.sub(r'[^\w\s/,-]', '', date_str).strip()
        
        date_formats = [
            '%m/%d/%Y',
            '%d/%m/%Y',
            '%Y-%m-%d',
            '%B %d, %Y',
            '%b %d, %Y',
            '%Y/%m/%d'
        ]
        
        for fmt in date_formats:
            try:
                return datetime.strptime(date_str, fmt).replace(tzinfo=timezone.utc)
            except ValueError:
                continue
        
        return datetime.now(timezone.utc)
    
    def _matches_criteria(self, job_data: Dict, search_terms: List[str], location: str) -> bool:
        """Check if job matches search criteria"""
        if not job_data:
            return False
        
        # Check search terms
        searchable_text = " ".join([
            job_data.get('title', ''),
            job_data.get('description', ''),
            " ".join(job_data.get('skills', []))
        ]).lower()
        
        if search_terms:
            has_match = any(term.lower() in searchable_text for term in search_terms)
            if not has_match:
                return False
        
        # Check location (if specified)
        if location:
            job_location = job_data.get('location', '').lower()
            if location.lower() not in job_location and 'remote' not in job_location:
                return False
        
        return True
    
    def _extract_salary_from_text(self, description: str) -> tuple:
        """Extract salary range from job description"""
        salary_info = self.extract_salary_info(description)
        return salary_info['min'], salary_info['max']
    
    def _extract_skills_from_text(self, text: str) -> List[str]:
        """Extract skills from job text"""
        return self.extract_skills_from_text(text)
    
    def _determine_location_type(self, location: str, description: str) -> str:
        """Determine location type"""
        return self.determine_location_type('', description, location)