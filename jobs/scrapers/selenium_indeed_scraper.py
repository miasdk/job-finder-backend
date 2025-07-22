"""
Selenium-based Indeed scraper inspired by https://github.com/Eben001/IndeedJobScraper
Uses headless Chrome to bypass anti-bot measures
"""

import logging
import time
from datetime import datetime, timezone
from typing import List, Dict, Optional
from urllib.parse import urlencode, quote_plus

try:
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.common.exceptions import TimeoutException, NoSuchElementException
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False

from .base_scraper import BaseScraper

logger = logging.getLogger('jobs')


class SeleniumIndeedScraper(BaseScraper):
    """Selenium-based Indeed scraper to bypass anti-bot measures"""
    
    def __init__(self, user_preferences=None):
        super().__init__(user_preferences)
        self.base_url = "https://www.indeed.com"
        self.driver = None
        
        if not SELENIUM_AVAILABLE:
            logger.warning("Selenium not available - install with: pip install selenium")
    
    def _setup_driver(self):
        """Set up headless Chrome driver"""
        if not SELENIUM_AVAILABLE:
            return None
            
        try:
            chrome_options = Options()
            chrome_options.add_argument("--headless")  # Run in background
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-blink-features=AutomationControlled")
            chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
            chrome_options.add_experimental_option('useAutomationExtension', False)
            chrome_options.add_argument("--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
            
            # Try to create driver (will work if Chrome/ChromeDriver is installed)
            driver = webdriver.Chrome(options=chrome_options)
            driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            return driver
            
        except Exception as e:
            logger.error(f"Failed to setup Chrome driver: {e}")
            return None
    
    def scrape_jobs(self, search_terms: List[str] = None, location: str = None) -> List[Dict]:
        """
        Scrape jobs from Indeed using Selenium
        """
        if not SELENIUM_AVAILABLE:
            logger.warning("Selenium not available - skipping Indeed scraping")
            return []
            
        jobs = []
        
        if not search_terms:
            search_terms = self.get_search_terms()
        
        if not location:
            locations = self.get_locations()
        else:
            locations = [location]
        
        self.driver = self._setup_driver()
        if not self.driver:
            logger.error("Failed to setup browser driver")
            return []
        
        try:
            # Limit search to avoid overwhelming Indeed
            for search_term in search_terms[:2]:
                for loc in locations[:2]:
                    try:
                        batch_jobs = self._scrape_for_term_and_location(search_term, loc)
                        jobs.extend(batch_jobs)
                        time.sleep(3)  # Be respectful to Indeed
                    except Exception as e:
                        logger.error(f"Error scraping Indeed for {search_term} in {loc}: {e}")
                        continue
            
            logger.info(f"Selenium Indeed scraper found {len(jobs)} jobs")
            return jobs
            
        finally:
            if self.driver:
                self.driver.quit()
    
    def _scrape_for_term_and_location(self, search_term: str, location: str) -> List[Dict]:
        """Scrape jobs for specific search term and location"""
        jobs = []
        
        try:
            # Build search URL
            params = {
                'q': search_term,
                'l': location,
                'sort': 'date',
                'fromage': '14'  # Last 14 days
            }
            
            search_url = f"{self.base_url}/jobs?{urlencode(params)}"
            logger.info(f"Searching Indeed: {search_url}")
            
            # Navigate to search page
            self.driver.get(search_url)
            
            # Wait for page to load
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, '[data-jk]'))
            )
            
            # Find job cards
            job_elements = self.driver.find_elements(By.CSS_SELECTOR, '[data-jk]')
            logger.info(f"Found {len(job_elements)} job elements")
            
            for job_element in job_elements[:10]:  # Limit to first 10 jobs
                try:
                    job_data = self._extract_job_from_element(job_element)
                    if job_data and self._is_relevant_job(job_data, search_term):
                        jobs.append(job_data)
                except Exception as e:
                    logger.error(f"Error extracting job: {e}")
                    continue
            
        except TimeoutException:
            logger.error("Timeout waiting for Indeed page to load")
        except Exception as e:
            logger.error(f"Error in Indeed scraping: {e}")
        
        return jobs
    
    def _extract_job_from_element(self, element) -> Optional[Dict]:
        """Extract job data from Selenium WebElement"""
        try:
            # Get job key for URL
            job_key = element.get_attribute('data-jk')
            if not job_key:
                return None
            
            job_url = f"https://www.indeed.com/viewjob?jk={job_key}"
            
            # Extract title
            try:
                title_elem = element.find_element(By.CSS_SELECTOR, 'h2 a span[title]')
                title = title_elem.get_attribute('title')
            except NoSuchElementException:
                try:
                    title_elem = element.find_element(By.CSS_SELECTOR, 'h2 a span')
                    title = title_elem.text
                except NoSuchElementException:
                    return None
            
            # Extract company
            try:
                company_elem = element.find_element(By.CSS_SELECTOR, '[data-testid="company-name"]')
                company = company_elem.text
            except NoSuchElementException:
                company = "Unknown Company"
            
            # Extract location
            try:
                location_elem = element.find_element(By.CSS_SELECTOR, '[data-testid="job-location"]')
                location = location_elem.text
            except NoSuchElementException:
                location = "Location not specified"
            
            # Extract salary if available
            salary_min, salary_max = None, None
            try:
                salary_elem = element.find_element(By.CSS_SELECTOR, '[data-testid="salary-snippet"]')
                salary_text = salary_elem.text
                salary_min, salary_max = self._parse_salary(salary_text)
            except NoSuchElementException:
                pass
            
            # Extract snippet/description
            description = ""
            try:
                snippet_elem = element.find_element(By.CSS_SELECTOR, '[data-testid="job-snippet"]')
                description = snippet_elem.text
            except NoSuchElementException:
                pass
            
            # Determine attributes
            location_type = self._determine_location_type(location, description)
            experience_level = self._determine_experience_level(title, description)
            skills = self.extract_skills_from_text(f"{title} {description}")
            
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
                'posted_date': datetime.now(timezone.utc),
                'source_url': job_url,
                'source': 'Indeed (Selenium)',
                'external_id': job_key,
            }
            
        except Exception as e:
            logger.error(f"Error extracting job element: {e}")
            return None
    
    def _parse_salary(self, salary_text: str) -> tuple:
        """Parse salary information"""
        import re
        
        if not salary_text:
            return None, None
        
        # Clean text
        salary_text = salary_text.replace('$', '').replace(',', '').lower()
        
        # Look for ranges
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
        """Determine location type"""
        text = f"{location} {description}".lower()
        
        if any(keyword in text for keyword in ['remote', 'work from home', 'telecommute']):
            return 'remote'
        elif any(keyword in text for keyword in ['hybrid', 'flexible']):
            return 'hybrid'
        else:
            return 'onsite'
    
    def _determine_experience_level(self, title: str, description: str) -> str:
        """Determine experience level"""
        text = f"{title} {description}".lower()
        
        if any(keyword in text for keyword in ['senior', 'lead', 'principal', 'staff']):
            return 'senior'
        elif any(keyword in text for keyword in ['entry', 'junior', 'graduate', 'new grad']):
            return 'entry'
        elif any(keyword in text for keyword in ['mid', 'intermediate', 'experienced']):
            return 'mid'
        else:
            return 'junior'
    
    def _is_relevant_job(self, job_data: Dict, search_term: str) -> bool:
        """Check if job is relevant"""
        if not job_data:
            return False
        
        title_desc = f"{job_data.get('title', '')} {job_data.get('description', '')}".lower()
        
        # Must contain relevant keywords
        relevant_keywords = ['python', 'django', 'backend', 'full stack', 'software engineer', 'developer']
        
        return any(keyword in title_desc for keyword in relevant_keywords)