import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from urllib.parse import quote_plus, urljoin
import requests
from bs4 import BeautifulSoup
import time
from .base_scraper import BaseScraper
from .rss_parser import IndeedRSSManager

logger = logging.getLogger('jobs')

class IndeedRSScraper(BaseScraper):
    """Scraper for Indeed RSS feeds using custom RSS parser"""
    
    def __init__(self):
        super().__init__()
        self.rss_manager = IndeedRSSManager()
        self.rss_delay = 2  # Delay between RSS requests
    
    def fetch_job_details(self, job_url: str) -> Dict:
        """Fetch additional job details from Indeed job page"""
        try:
            response = self.session.get(job_url, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Extract full job description
            job_description = ""
            desc_div = soup.find('div', {'class': 'jobsearch-jobDescriptionText'}) or \
                      soup.find('div', {'id': 'jobDescriptionText'}) or \
                      soup.find('div', {'class': 'jobsearch-JobComponent-description'})
            
            if desc_div:
                job_description = self.clean_text(desc_div.get_text())
            
            # Extract company information
            company_info = {}
            company_div = soup.find('div', {'data-testid': 'inlineHeader-companyName'}) or \
                         soup.find('span', {'class': 'icl-u-lg-mr--sm'}) or \
                         soup.find('a', {'data-testid': 'company-name'})
            
            if company_div:
                company_info['name'] = self.clean_text(company_div.get_text())
            
            # Extract salary if available
            salary_info = {'min': None, 'max': None}
            salary_span = soup.find('span', {'class': 'icl-u-xs-mr--xs'}) or \
                         soup.find('div', {'class': 'salary-snippet'})
            
            if salary_span:
                salary_text = salary_span.get_text()
                salary_info = self.extract_salary_info(salary_text)
            
            return {
                'description': job_description,
                'company_info': company_info,
                'salary_info': salary_info
            }
            
        except Exception as e:
            logger.warning(f"Failed to fetch job details from {job_url}: {str(e)}")
            return {'description': '', 'company_info': {}, 'salary_info': {'min': None, 'max': None}}
    
    def parse_rss_jobs(self, rss_jobs: List[Dict]) -> List[Dict]:
        """Parse RSS job entries and fetch additional details"""
        processed_jobs = []
        
        for job_entry in rss_jobs[:20]:  # Limit to 20 jobs per query
            try:
                # Extract basic information from RSS
                job_data = {
                    'title': self.clean_text(job_entry.get('title', '')),
                    'link': job_entry.get('link', ''),
                    'published': job_entry.get('published'),
                    'summary': self.clean_text(job_entry.get('summary', '')),
                    'source': 'indeed',
                    'published_date': job_entry.get('published_date')
                }
                
                # Extract location from summary or use default
                location_match = "New York, NY"  # Default for now
                job_data['location'] = location_match
                
                # Get additional details by scraping the job page
                time.sleep(1)  # Be respectful to Indeed's servers
                details = self.fetch_job_details(job_entry.get('link', ''))
                job_data.update(details)
                
                # Use summary if no description found
                if not job_data.get('description') and job_data['summary']:
                    job_data['description'] = job_data['summary']
                
                processed_jobs.append(job_data)
                
            except Exception as e:
                logger.error(f"Error processing RSS entry: {str(e)}")
                continue
        
        logger.info(f"Successfully processed {len(processed_jobs)} jobs from RSS feed")
        return processed_jobs
    
    def scrape_jobs(self, search_terms: List[str], location: str = "New York, NY") -> List[Dict]:
        """Scrape jobs from Indeed RSS feeds for multiple search terms"""
        logger.info(f"Starting Indeed job scraping for {len(search_terms)} search terms in {location}")
        
        # Get raw RSS jobs using our custom parser
        raw_rss_jobs = self.rss_manager.get_jobs_from_rss(search_terms, location)
        
        # Process RSS jobs to extract details
        processed_jobs = self.parse_rss_jobs(raw_rss_jobs)
        
        # Convert to final job format
        all_jobs = []
        for job_data in processed_jobs:
            try:
                processed_job = self.process_job_data(job_data, location)
                if processed_job:
                    all_jobs.append(processed_job)
            except Exception as e:
                logger.error(f"Error processing job data: {str(e)}")
                continue
        
        logger.info(f"Successfully scraped {len(all_jobs)} jobs from Indeed")
        return all_jobs
    
    def process_job_data(self, raw_job: Dict, location: str) -> Optional[Dict]:
        """Process and normalize raw job data"""
        try:
            # Extract company name
            company_name = "Unknown Company"
            if raw_job.get('company_info', {}).get('name'):
                company_name = raw_job['company_info']['name']
            
            # Combine title and description for skill extraction
            full_text = f"{raw_job['title']} {raw_job['description']}"
            
            # Extract skills
            required_skills = self.extract_skills_from_text(full_text)
            
            # Determine experience level
            experience_level = self.determine_experience_level(raw_job['title'], raw_job['description'])
            
            # Determine location type
            location_type = self.determine_location_type(raw_job['title'], raw_job['description'], location)
            
            # Extract salary
            salary_info = raw_job.get('salary_info', {'min': None, 'max': None})
            if not salary_info['min'] and not salary_info['max']:
                salary_info = self.extract_salary_info(raw_job['description'])
            
            # Check if entry-level friendly
            is_entry_level_friendly = any(keyword in full_text.lower() for keyword in [
                'entry', 'junior', 'new grad', 'graduate', 'no experience', 'training provided'
            ])
            
            processed_job = {
                'title': raw_job['title'],
                'company_name': company_name,
                'description': raw_job['description'],
                'location': location,
                'location_type': location_type,
                'source': 'indeed',
                'source_url': raw_job['link'],
                'required_skills': required_skills,
                'salary_min': salary_info['min'],
                'salary_max': salary_info['max'],
                'experience_level': experience_level,
                'posted_date': raw_job.get('published_date'),
                'is_entry_level_friendly': is_entry_level_friendly,
                'employment_type': 'full_time'  # Default, could be improved with better parsing
            }
            
            return processed_job
            
        except Exception as e:
            logger.error(f"Error processing job data: {str(e)}")
            return None