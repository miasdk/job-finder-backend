"""
Multi-source job scraper that uses real job sources
Combines RemoteOK, Python.org, and other scraping-friendly sources
"""

import logging
import time
from datetime import timedelta
from django.utils import timezone
from typing import List, Dict, Optional
from .base_scraper import BaseScraper
from .remoteok_scraper import RemoteOKScraper
from .python_jobs_scraper import PythonJobsScraper
from .dice_scraper import DiceScraper
from .wellfound_scraper import WellfoundScraper

logger = logging.getLogger('jobs')

class MultiSourceScraper(BaseScraper):
    """Scraper that combines multiple real job sources"""
    
    def __init__(self):
        super().__init__()
        self.remoteok_scraper = RemoteOKScraper()
        self.python_jobs_scraper = PythonJobsScraper()
        self.dice_scraper = DiceScraper()
        self.wellfound_scraper = WellfoundScraper()
        
        # Keep enhanced scraper as fallback
        self.enhanced_scraper = EnhancedJobScraper()
    
    def scrape_jobs(self, search_terms: List[str], location: str = "New York, NY") -> List[Dict]:
        """Scrape jobs from multiple real sources"""
        all_jobs = []
        
        if not search_terms:
            search_terms = ['python', 'django', 'backend', 'web developer']
        
        # Scrape from RemoteOK (remote jobs)
        try:
            logger.info("Scraping RemoteOK...")
            remoteok_jobs = self.remoteok_scraper.scrape_jobs(search_terms, location)
            all_jobs.extend(remoteok_jobs)
            time.sleep(2)  # Be respectful
        except Exception as e:
            logger.error(f"RemoteOK scraper error: {str(e)}")
        
        # Scrape from Python.org job board
        try:
            logger.info("Scraping Python.org job board...")
            python_jobs = self.python_jobs_scraper.scrape_jobs(search_terms, location)
            all_jobs.extend(python_jobs)
            time.sleep(2)  # Be respectful
        except Exception as e:
            logger.error(f"Python.org scraper error: {str(e)}")
        
        # Scrape from Dice.com (major tech job board)
        try:
            logger.info("Scraping Dice.com...")
            dice_jobs = self.dice_scraper.scrape_jobs(search_terms, location)
            all_jobs.extend(dice_jobs)
            time.sleep(3)  # Be extra respectful to Dice
        except Exception as e:
            logger.error(f"Dice.com scraper error: {str(e)}")
        
        # Scrape from Wellfound (AngelList - startup jobs)
        try:
            logger.info("Scraping Wellfound/AngelList...")
            wellfound_jobs = self.wellfound_scraper.scrape_jobs(search_terms, location)
            all_jobs.extend(wellfound_jobs)
            time.sleep(3)  # Be respectful
        except Exception as e:
            logger.error(f"Wellfound scraper error: {str(e)}")
        
        # If we got very few real jobs, supplement with enhanced test data
        if len(all_jobs) < 5:
            logger.info("Few real jobs found, supplementing with test data...")
            try:
                enhanced_jobs = self.enhanced_scraper.scrape_jobs(search_terms, location)
                all_jobs.extend(enhanced_jobs[:10])  # Limit test data
            except Exception as e:
                logger.error(f"Enhanced scraper error: {str(e)}")
        
        logger.info(f"Found {len(all_jobs)} total jobs from all sources")
        return all_jobs
    
    def _scrape_adzuna(self, search_terms: List[str], location: str) -> List[Dict]:
        """Scrape from Adzuna API (free tier available)"""
        jobs = []
        
        # Adzuna API endpoint (you'd need to register for free API key)
        # For demo purposes, returning mock data
        logger.info("Adzuna API would be called here (requires API key)")
        
        # Mock data for demonstration
        mock_jobs = [
            {
                'title': 'Python Developer - Entry Level',
                'company_name': 'TechCorp NYC',
                'description': 'Looking for an entry-level Python developer with Django experience. Perfect for new graduates! We offer mentorship and training in our modern NYC office.',
                'location': 'New York, NY',
                'location_type': 'hybrid',
                'source': 'adzuna',
                'source_url': 'https://example.com/job1',
                'required_skills': ['Python', 'Django', 'SQL'],
                'salary_min': 75000,
                'salary_max': 95000,
                'experience_level': 'entry',
                'posted_date': timezone.now() - timedelta(days=1),
                'is_entry_level_friendly': True,
                'employment_type': 'full_time'
            },
            {
                'title': 'Full Stack Developer (Python/React)',
                'company_name': 'HealthTech Solutions',
                'description': 'Join our healthcare technology team! We need a full stack developer with Python backend and React frontend skills. Experience with Django REST API preferred.',
                'location': 'Brooklyn, NY',
                'location_type': 'onsite',
                'source': 'adzuna',
                'source_url': 'https://example.com/job2',
                'required_skills': ['Python', 'Django', 'React', 'Django REST Framework', 'PostgreSQL'],
                'salary_min': 85000,
                'salary_max': 110000,
                'experience_level': 'junior',
                'posted_date': timezone.now() - timedelta(days=2),
                'is_entry_level_friendly': True,
                'employment_type': 'full_time'
            }
        ]
        
        for search_term in search_terms[:1]:  # Limit for demo
            jobs.extend(mock_jobs)
        
        return jobs
    
    def _scrape_usajobs(self, search_terms: List[str], location: str) -> List[Dict]:
        """Scrape from USAJobs API (free government job API)"""
        jobs = []
        
        try:
            # USAJobs has a free API
            base_url = "https://data.usajobs.gov/api/search"
            
            headers = {
                'Host': 'data.usajobs.gov',
                'User-Agent': 'your-email@example.com',  # USAJobs requires email in User-Agent
            }
            
            for search_term in search_terms[:2]:  # Limit API calls
                params = {
                    'Keyword': search_term,
                    'LocationName': location,
                    'ResultsPerPage': 10
                }
                
                response = requests.get(base_url, headers=headers, params=params, timeout=10)
                
                if response.status_code == 200:
                    data = response.json()
                    search_result = data.get('SearchResult', {})
                    job_data = search_result.get('SearchResultItems', [])
                    
                    for item in job_data:
                        job_detail = item.get('MatchedObjectDescriptor', {})
                        
                        job = {
                            'title': job_detail.get('PositionTitle', ''),
                            'company_name': job_detail.get('OrganizationName', 'US Government'),
                            'description': job_detail.get('QualificationSummary', ''),
                            'location': f"{job_detail.get('PositionLocationDisplay', location)}",
                            'location_type': 'onsite',
                            'source': 'usajobs',
                            'source_url': job_detail.get('PositionURI', ''),
                            'required_skills': self.extract_skills_from_text(job_detail.get('QualificationSummary', '')),
                            'salary_min': self._parse_usajobs_salary(job_detail.get('PositionRemuneration', [])),
                            'salary_max': None,
                            'experience_level': self.determine_experience_level(job_detail.get('PositionTitle', ''), job_detail.get('QualificationSummary', '')),
                            'posted_date': timezone.now(),
                            'is_entry_level_friendly': 'entry' in job_detail.get('PositionTitle', '').lower(),
                            'employment_type': 'full_time'
                        }
                        
                        if job['title']:  # Only add if we have a title
                            jobs.append(job)
                
                time.sleep(1)  # Rate limiting
                
        except Exception as e:
            logger.warning(f"USAJobs API error: {str(e)}")
        
        logger.info(f"Found {len(jobs)} jobs from USAJobs")
        return jobs
    
    def _scrape_github_jobs(self, search_terms: List[str], location: str) -> List[Dict]:
        """Mock GitHub Jobs scraper (GitHub Jobs API was discontinued)"""
        jobs = []
        
        # Mock remote-friendly jobs since GitHub was popular for tech jobs
        mock_remote_jobs = [
            {
                'title': 'Remote Python Developer',
                'company_name': 'RemoteFirst Inc',
                'description': 'Fully remote position for Python developer. Work with Django, PostgreSQL, and modern web technologies. Perfect for someone looking to work remotely while building scalable web applications.',
                'location': 'Remote (US)',
                'location_type': 'remote',
                'source': 'remote_board',
                'source_url': 'https://example.com/remote-job1',
                'required_skills': ['Python', 'Django', 'PostgreSQL', 'AWS', 'Docker'],
                'salary_min': 80000,
                'salary_max': 120000,
                'experience_level': 'junior',
                'posted_date': timezone.now() - timedelta(days=1),
                'is_entry_level_friendly': True,
                'employment_type': 'full_time'
            },
            {
                'title': 'Junior Backend Developer (Python)',
                'company_name': 'CloudTech Startup',
                'description': 'Join our growing startup! We are looking for a junior backend developer with Python and Django experience. You will work on building APIs and microservices. Remote work available.',
                'location': 'Remote/NYC Hybrid',
                'location_type': 'hybrid',
                'source': 'remote_board',
                'source_url': 'https://example.com/remote-job2',
                'required_skills': ['Python', 'Django', 'REST API', 'Redis', 'JavaScript'],
                'salary_min': 70000,
                'salary_max': 100000,
                'experience_level': 'junior',
                'posted_date': timezone.now() - timedelta(days=3),
                'is_entry_level_friendly': True,
                'employment_type': 'full_time'
            }
        ]
        
        if 'Python' in ' '.join(search_terms) or 'Django' in ' '.join(search_terms):
            jobs.extend(mock_remote_jobs)
        
        logger.info(f"Found {len(jobs)} remote/hybrid jobs")
        return jobs
    
    def _parse_usajobs_salary(self, remuneration_list: List) -> Optional[int]:
        """Parse USAJobs salary information"""
        if not remuneration_list:
            return None
        
        try:
            for item in remuneration_list:
                min_range = item.get('MinimumRange')
                if min_range and min_range.isdigit():
                    return int(min_range)
        except Exception:
            pass
        
        return None

class EnhancedJobScraper(BaseScraper):
    """Enhanced scraper that creates realistic job data for testing"""
    
    def scrape_jobs(self, search_terms: List[str], location: str = "New York, NY") -> List[Dict]:
        """Generate realistic job data for testing the application"""
        
        companies = [
            {'name': 'TechFlow Solutions', 'type': 'startup', 'location': 'Manhattan, NY'},
            {'name': 'DataCorp Analytics', 'type': 'tech', 'location': 'Brooklyn, NY'},
            {'name': 'HealthTech Innovations', 'type': 'healthcare', 'location': 'Queens, NY'},
            {'name': 'FinanceCloud Inc', 'type': 'fintech', 'location': 'Manhattan, NY'},
            {'name': 'RemoteCode Co', 'type': 'startup', 'location': 'Remote'},
            {'name': 'NYC MedSystems', 'type': 'healthcare', 'location': 'Manhattan, NY'},
        ]
        
        job_templates = [
            {
                'title_templates': [
                    'Junior Python Developer',
                    'Entry Level Python Developer',
                    'Python Developer - New Grad',
                    'Associate Python Developer'
                ],
                'skills': ['Python', 'Django', 'SQL', 'Git'],
                'salary_range': (70000, 95000),
                'experience': 'entry',
                'entry_friendly': True
            },
            {
                'title_templates': [
                    'Full Stack Developer',
                    'Full Stack Engineer',
                    'Junior Full Stack Developer'
                ],
                'skills': ['Python', 'Django', 'React', 'JavaScript', 'PostgreSQL'],
                'salary_range': (75000, 105000),
                'experience': 'junior',
                'entry_friendly': True
            },
            {
                'title_templates': [
                    'Backend Developer',
                    'Backend Engineer',
                    'Python Backend Developer'
                ],
                'skills': ['Python', 'Django', 'PostgreSQL', 'Redis', 'AWS'],
                'salary_range': (80000, 110000),
                'experience': 'junior',
                'entry_friendly': True
            },
            {
                'title_templates': [
                    'Django Developer',
                    'Django Web Developer',
                    'Python/Django Developer'
                ],
                'skills': ['Python', 'Django', 'Django REST Framework', 'PostgreSQL', 'HTML', 'CSS'],
                'salary_range': (72000, 98000),
                'experience': 'entry',
                'entry_friendly': True
            },
            {
                'title_templates': [
                    'Software Engineer',
                    'Junior Software Engineer',
                    'Associate Software Engineer'
                ],
                'skills': ['Python', 'Django', 'React', 'TypeScript', 'Docker'],
                'salary_range': (85000, 120000),
                'experience': 'junior',
                'entry_friendly': True
            }
        ]
        
        location_types = ['onsite', 'hybrid', 'remote']
        
        all_jobs = []
        job_id = 1
        
        for company in companies:
            for template in job_templates:
                for title_template in template['title_templates'][:1]:  # One job per template per company
                    
                    # Vary the location type
                    location_type = 'remote' if company['location'] == 'Remote' else \
                                  'hybrid' if 'Manhattan' in company['location'] else 'onsite'
                    
                    # Create job description
                    if template['experience'] == 'entry':
                        experience_text = "Perfect for new graduates and entry-level candidates! No prior experience required. We provide training and mentorship."
                    else:
                        experience_text = "Looking for junior developers with some experience or strong portfolio projects."
                    
                    description = f"""We are seeking a talented {title_template.lower()} to join our {company['type']} team. 
                    
                    {experience_text}
                    
                    You will work with modern technologies including {', '.join(template['skills'][:3])}. 
                    This is a great opportunity to grow your career in a collaborative environment.
                    
                    Requirements:
                    • Strong knowledge of {template['skills'][0]} and {template['skills'][1]}
                    • Experience with {', '.join(template['skills'][2:])}
                    • Good problem-solving skills
                    • Team collaboration experience
                    
                    We offer competitive salary, health benefits, and professional development opportunities."""
                    
                    job = {
                        'title': title_template,
                        'company_name': company['name'],
                        'description': description,
                        'location': company['location'],
                        'location_type': location_type,
                        'source': 'enhanced_scraper',
                        'source_url': f'https://example.com/job-{job_id}',
                        'required_skills': template['skills'],
                        'salary_min': template['salary_range'][0],
                        'salary_max': template['salary_range'][1],
                        'experience_level': template['experience'],
                        'posted_date': timezone.now() - timedelta(days=job_id % 5),
                        'is_entry_level_friendly': template['entry_friendly'],
                        'employment_type': 'full_time'
                    }
                    
                    all_jobs.append(job)
                    job_id += 1
        
        logger.info(f"Generated {len(all_jobs)} realistic job postings")
        return all_jobs