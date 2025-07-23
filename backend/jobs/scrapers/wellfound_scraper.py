"""
Wellfound (AngelList) job scraper for startup jobs.
Wellfound has 130K+ jobs with salary/equity info shown upfront.
"""

import requests
from bs4 import BeautifulSoup
from datetime import datetime, timezone, timedelta
from typing import List, Dict
import re
import time
import json
from urllib.parse import urlencode, urljoin
from .base_scraper import BaseScraper


class WellfoundScraper(BaseScraper):
    """Scraper for Wellfound (formerly AngelList) startup job listings"""
    
    def __init__(self, user_preferences=None):
        super().__init__(user_preferences)
        self.base_url = "https://wellfound.com"
        self.search_url = "https://wellfound.com/jobs"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Referer': 'https://wellfound.com',
        }
    
    def scrape_jobs(self, search_terms: List[str] = None, location: str = "New York, NY") -> List[Dict]:
        """
        Scrape jobs from Wellfound
        
        Args:
            search_terms: List of search terms
            location: Location to search
            
        Returns:
            List of job dictionaries
        """
        jobs = []
        
        if not search_terms:
            search_terms = ['python', 'django', 'backend', 'full stack']
        
        try:
            # Wellfound uses role-based search
            role_mappings = {
                'python': 'Software Engineer',
                'django': 'Backend Engineer', 
                'backend': 'Backend Engineer',
                'full stack': 'Full Stack Engineer',
                'frontend': 'Frontend Engineer',
                'react': 'Frontend Engineer'
            }
            
            # Get unique roles to search
            roles_to_search = set()
            for term in search_terms:
                role = role_mappings.get(term.lower(), 'Software Engineer')
                roles_to_search.add(role)
            
            # Search for each role
            for role in list(roles_to_search)[:2]:  # Limit to avoid overwhelming
                print(f"Searching Wellfound for: {role}")
                
                role_jobs = self._search_role(role, location)
                jobs.extend(role_jobs)
                
                time.sleep(3)  # Be respectful
            
            print(f"Wellfound: Found {len(jobs)} matching jobs total")
            return jobs
            
        except requests.RequestException as e:
            print(f"Error scraping Wellfound: {e}")
            return []
        except Exception as e:
            print(f"Unexpected error in Wellfound scraper: {e}")
            return []
    
    def _search_role(self, role: str, location: str) -> List[Dict]:
        """Search for jobs by role and location"""
        jobs = []
        
        try:
            # Build search URL - Wellfound uses role-based filtering
            params = {
                'role': role,
                'location': location,
                'remote': 'true'  # Include remote jobs
            }
            
            search_url = f"{self.search_url}?{urlencode(params)}"
            
            # Get search results
            response = self.session.get(search_url, headers=self.headers, timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Find job listings
            job_elements = self._find_job_elements(soup)
            
            print(f"Found {len(job_elements)} job elements for {role}")
            
            # Process each job
            for job_elem in job_elements[:8]:  # Limit per role
                job_data = self._process_job_element(job_elem)
                if job_data:
                    jobs.append(job_data)
            
            return jobs
            
        except Exception as e:
            print(f"Error searching Wellfound for {role}: {e}")
            return []
    
    def _find_job_elements(self, soup: BeautifulSoup) -> List:
        """Find job elements on Wellfound search page"""
        # Try different selectors for job cards
        selectors = [
            '[data-test="JobCard"]',
            '.job-card',
            '[data-test*="job"]',
            '.startup-job-listing',
            '[class*="JobCard"]',
            '[data-cy="job-card"]'
        ]
        
        job_elements = []
        for selector in selectors:
            elements = soup.select(selector)
            if elements:
                job_elements = elements
                break
        
        # Fallback: look for article elements or divs with job-like classes
        if not job_elements:
            job_elements = soup.find_all(['article', 'div'], attrs={
                'class': re.compile(r'job|card|listing', re.I)
            })
        
        return job_elements
    
    def _process_job_element(self, element) -> Dict:
        """Process individual job element"""
        try:
            # Extract title
            title = self._extract_title(element)
            if not title:
                return None
            
            # Extract company
            company = self._extract_company(element)
            
            # Extract location
            location = self._extract_location(element)
            
            # Extract salary/compensation
            salary_min, salary_max = self._extract_compensation(element)
            
            # Extract job URL
            job_url = self._extract_job_url(element)
            
            # Extract description/tags
            description = self._extract_description(element)
            
            # Determine attributes
            location_type = self.determine_location_type(title, description, location)
            experience_level = self.determine_experience_level(title, description)
            skills = self.extract_skills_from_text(f"{title} {description}")
            
            # Wellfound jobs are typically startup-friendly for entry level
            is_entry_friendly = any(keyword in f"{title} {description}".lower() 
                                  for keyword in ['junior', 'entry', 'new grad', 'associate'])
            
            job_data = {
                'title': title,
                'company': company or 'Startup Company',
                'description': description,
                'location': location or 'Remote',
                'location_type': location_type,
                'salary_min': salary_min,
                'salary_max': salary_max,
                'salary_currency': 'USD',
                'experience_level': experience_level,
                'job_type': 'full_time',
                'skills': skills,
                'posted_date': datetime.now(timezone.utc) - timedelta(days=2),  # Assume recent
                'source_url': job_url or 'https://wellfound.com',
                'source': 'Wellfound',
                'external_id': job_url.split('/')[-1] if job_url else str(hash(title + company)),
                'raw_data': {'element_html': str(element)[:500]}
            }
            
            return job_data
            
        except Exception as e:
            print(f"Error processing Wellfound job element: {e}")
            return None
    
    def _extract_title(self, element) -> str:
        """Extract job title"""
        title_selectors = [
            'h2 a', 'h3 a', '.job-title', '[data-test="job-title"]',
            'h2', 'h3', '.title', '[data-cy="job-title"]',
            'a[href*="/jobs/"]'
        ]
        
        for selector in title_selectors:
            elem = element.select_one(selector)
            if elem:
                title = elem.get_text(strip=True)
                if title and len(title) > 2:
                    return title
        
        return ""
    
    def _extract_company(self, element) -> str:
        """Extract company name"""
        company_selectors = [
            '.company-name', '[data-test="company-name"]', '.startup-name',
            'h4 a', 'h3 a[href*="/companies/"]', '.company',
            '[data-cy="company-name"]'
        ]
        
        for selector in company_selectors:
            elem = element.select_one(selector)
            if elem:
                company = elem.get_text(strip=True)
                if company and len(company) > 1:
                    return company
        
        return ""
    
    def _extract_location(self, element) -> str:
        """Extract job location"""
        location_selectors = [
            '.location', '[data-test="job-location"]', '.job-location',
            '[data-cy="location"]', '.loc'
        ]
        
        for selector in location_selectors:
            elem = element.select_one(selector)
            if elem:
                location = elem.get_text(strip=True)
                if location:
                    return location
        
        # Look for common location patterns in text
        text = element.get_text()
        location_patterns = [
            r'\b(New York|NYC|San Francisco|Remote|Austin|Seattle|Boston|Chicago|Los Angeles)\b'
        ]
        
        for pattern in location_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1)
        
        return ""
    
    def _extract_compensation(self, element) -> tuple:
        """Extract salary/equity compensation"""
        # Wellfound often shows salary ranges and equity
        text = element.get_text()
        
        # Use base scraper salary extraction
        salary_info = self.extract_salary_info(text)
        
        # Look for equity mentions (common in startups)
        equity_patterns = [
            r'(\d+\.?\d*%)\s*equity',
            r'equity:\s*(\d+\.?\d*%)',
            r'(\d+\.?\d*%)\s*-\s*(\d+\.?\d*%)\s*equity'
        ]
        
        # If we found equity but no salary, estimate based on role
        if not salary_info['min'] and any(re.search(p, text.lower()) for p in equity_patterns):
            # Startup salary estimates
            if 'senior' in text.lower():
                salary_info['min'] = 120000
                salary_info['max'] = 180000
            elif 'junior' in text.lower() or 'entry' in text.lower():
                salary_info['min'] = 80000
                salary_info['max'] = 120000
            else:
                salary_info['min'] = 100000
                salary_info['max'] = 150000
        
        return salary_info['min'], salary_info['max']
    
    def _extract_job_url(self, element) -> str:
        """Extract job detail URL"""
        link_selectors = [
            'h2 a', 'h3 a', '.job-title a', 'a[href*="/jobs/"]',
            '[data-test="job-title"] a'
        ]
        
        for selector in link_selectors:
            elem = element.select_one(selector)
            if elem and elem.get('href'):
                href = elem.get('href')
                if href.startswith('/'):
                    return urljoin(self.base_url, href)
                elif href.startswith('http'):
                    return href
        
        return ""
    
    def _extract_description(self, element) -> str:
        """Extract job description or summary"""
        desc_selectors = [
            '.job-description', '.description', '.summary', '.tags',
            '[data-test="job-description"]', '.job-summary'
        ]
        
        descriptions = []
        for selector in desc_selectors:
            elem = element.select_one(selector)
            if elem:
                desc = elem.get_text(strip=True)
                if desc and len(desc) > 10:
                    descriptions.append(desc)
        
        if descriptions:
            return ' '.join(descriptions)
        
        # Fallback: get limited text from element
        all_text = element.get_text(strip=True)
        cleaned_text = ' '.join(all_text.split())
        return cleaned_text[:300] if len(cleaned_text) > 300 else cleaned_text