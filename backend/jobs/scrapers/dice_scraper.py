"""
Dice.com job scraper for tech jobs.
Dice is one of the largest tech job boards with good scraping access.
"""

import requests
from bs4 import BeautifulSoup
from datetime import datetime, timezone, timedelta
from typing import List, Dict
import re
import time
from urllib.parse import urlencode, urljoin
from .base_scraper import BaseScraper


class DiceScraper(BaseScraper):
    """Scraper for Dice.com tech job listings"""
    
    def __init__(self):
        super().__init__()
        self.base_url = "https://www.dice.com"
        self.search_url = "https://www.dice.com/jobs"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Referer': 'https://www.dice.com',
        }
    
    def scrape_jobs(self, search_terms: List[str] = None, location: str = "New York, NY") -> List[Dict]:
        """
        Scrape jobs from Dice.com
        
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
            # Search for each term
            for search_term in search_terms[:3]:  # Limit to avoid overwhelming
                print(f"Searching Dice for: {search_term}")
                
                # Build search URL
                params = {
                    'q': search_term,
                    'location': location,
                    'radius': '30',  # 30 mile radius
                    'pageSize': '20'  # Results per page
                }
                
                search_url = f"{self.search_url}?{urlencode(params)}"
                
                # Get search results page
                response = self.session.get(search_url, headers=self.headers, timeout=30)
                response.raise_for_status()
                
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Find job cards
                job_cards = self._find_job_cards(soup)
                
                print(f"Found {len(job_cards)} job cards for '{search_term}'")
                
                # Process each job card
                for card in job_cards[:10]:  # Limit per search term
                    job_data = self._process_job_card(card)
                    if job_data and self._matches_criteria(job_data, search_terms, location):
                        jobs.append(job_data)
                
                time.sleep(2)  # Be respectful
            
            print(f"Dice.com: Found {len(jobs)} matching jobs total")
            return jobs
            
        except requests.RequestException as e:
            print(f"Error scraping Dice.com: {e}")
            return []
        except Exception as e:
            print(f"Unexpected error in Dice scraper: {e}")
            return []
    
    def _find_job_cards(self, soup: BeautifulSoup) -> List:
        """Find job card elements on Dice search results page"""
        # Try multiple selectors for job cards
        selectors = [
            '[data-testid="job-card"]',
            '.card',
            '[data-cy="job-card"]',
            '.job-card',
            '.search-result-job',
            'article[data-testid*="job"]'
        ]
        
        job_cards = []
        for selector in selectors:
            cards = soup.select(selector)
            if cards:
                job_cards = cards
                break
        
        # Fallback: look for common job listing patterns
        if not job_cards:
            # Look for divs with job-related attributes
            job_cards = soup.find_all(['div', 'article'], attrs={
                'class': re.compile(r'job|card|result', re.I)
            })
        
        return job_cards
    
    def _process_job_card(self, card) -> Dict:
        """Process individual job card to extract job data"""
        try:
            # Extract title
            title = self._extract_title(card)
            if not title:
                return None
            
            # Extract company
            company = self._extract_company(card)
            
            # Extract location
            location = self._extract_location(card)
            
            # Extract job URL
            job_url = self._extract_job_url(card)
            
            # Extract salary if visible
            salary_min, salary_max = self._extract_salary_from_card(card)
            
            # Extract snippet/description
            description = self._extract_description(card)
            
            # Determine location type and other attributes
            location_type = self.determine_location_type(title, description, location)
            experience_level = self.determine_experience_level(title, description)
            skills = self.extract_skills_from_text(f"{title} {description}")
            
            # Create job data
            job_data = {
                'title': title,
                'company': company or 'Not specified',
                'description': description,
                'location': location or 'New York, NY',
                'location_type': location_type,
                'salary_min': salary_min,
                'salary_max': salary_max,
                'salary_currency': 'USD',
                'experience_level': experience_level,
                'job_type': 'full_time',
                'skills': skills,
                'posted_date': datetime.now(timezone.utc) - timedelta(days=1),  # Assume recent
                'source_url': job_url or 'https://dice.com',
                'source': 'Dice.com',
                'external_id': job_url.split('/')[-1] if job_url else str(hash(title + company)),
                'raw_data': {'card_html': str(card)}
            }
            
            return job_data
            
        except Exception as e:
            print(f"Error processing Dice job card: {e}")
            return None
    
    def _extract_title(self, card) -> str:
        """Extract job title from card"""
        title_selectors = [
            'h2 a', 'h3 a', '.job-title a', '[data-testid="job-title"] a',
            'h2', 'h3', '.job-title', '[data-testid="job-title"]',
            'a[data-testid*="title"]'
        ]
        
        for selector in title_selectors:
            element = card.select_one(selector)
            if element:
                title = element.get_text(strip=True)
                if title and len(title) > 3:
                    return title
        
        return ""
    
    def _extract_company(self, card) -> str:
        """Extract company name from card"""
        company_selectors = [
            '[data-testid="job-company"] a', '.company a', '[data-cy="company-name"]',
            '[data-testid="job-company"]', '.company', '.employer',
            'a[data-testid*="company"]'
        ]
        
        for selector in company_selectors:
            element = card.select_one(selector)
            if element:
                company = element.get_text(strip=True)
                if company and len(company) > 1:
                    return company
        
        return ""
    
    def _extract_location(self, card) -> str:
        """Extract location from card"""
        location_selectors = [
            '[data-testid="job-location"]', '.location', '[data-cy="location"]',
            '.job-location', '.loc'
        ]
        
        for selector in location_selectors:
            element = card.select_one(selector)
            if element:
                location = element.get_text(strip=True)
                if location:
                    return location
        
        return ""
    
    def _extract_job_url(self, card) -> str:
        """Extract job detail URL from card"""
        # Look for main job link
        link_selectors = [
            'h2 a', 'h3 a', '.job-title a', '[data-testid="job-title"] a',
            'a[href*="/jobs/detail/"]', 'a[href*="/job/"]'
        ]
        
        for selector in link_selectors:
            element = card.select_one(selector)
            if element and element.get('href'):
                href = element.get('href')
                # Make absolute URL
                if href.startswith('/'):
                    return urljoin(self.base_url, href)
                elif href.startswith('http'):
                    return href
        
        return ""
    
    def _extract_salary_from_card(self, card) -> tuple:
        """Extract salary from job card if visible"""
        # Get all text from card
        card_text = card.get_text()
        
        # Use base scraper salary extraction
        salary_info = self.extract_salary_info(card_text)
        return salary_info['min'], salary_info['max']
    
    def _extract_description(self, card) -> str:
        """Extract job description/snippet from card"""
        desc_selectors = [
            '.job-description', '.description', '.snippet', '.summary',
            '[data-testid="job-description"]', '.job-snippet'
        ]
        
        for selector in desc_selectors:
            element = card.select_one(selector)
            if element:
                desc = element.get_text(strip=True)
                if desc and len(desc) > 20:
                    return desc
        
        # Fallback: get all text from card and clean it
        all_text = card.get_text(strip=True)
        # Remove extra whitespace and limit length
        cleaned_text = ' '.join(all_text.split())
        return cleaned_text[:500] if len(cleaned_text) > 500 else cleaned_text
    
    def _matches_criteria(self, job_data: Dict, search_terms: List[str], location: str) -> bool:
        """Check if job matches search criteria"""
        if not job_data:
            return False
        
        # Check for minimum required fields
        if not job_data.get('title') or not job_data.get('company'):
            return False
        
        # Check search terms
        searchable_text = " ".join([
            job_data.get('title', ''),
            job_data.get('description', ''),
            " ".join(job_data.get('skills', []))
        ]).lower()
        
        if search_terms:
            # Must match at least one search term
            has_match = any(term.lower() in searchable_text for term in search_terms)
            if not has_match:
                return False
        
        return True