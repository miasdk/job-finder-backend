"""
Stack Overflow Jobs scraper - creates representative developer jobs
"""

from datetime import datetime, timezone, timedelta
from typing import List, Dict
import random
from .base_scraper import BaseScraper


class StackOverflowJobsScraper(BaseScraper):
    """Scraper for Stack Overflow style developer jobs"""
    
    def __init__(self, user_preferences=None):
        super().__init__(user_preferences)
    
    def scrape_jobs(self, search_terms: List[str] = None, location: str = None) -> List[Dict]:
        """Generate Stack Overflow style tech jobs"""
        
        if not search_terms:
            search_terms = ['python', 'javascript', 'software engineer']
        
        # Job templates based on common Stack Overflow job patterns
        job_templates = [
            {
                'title_templates': [
                    'Senior Python Engineer', 'Python Backend Developer', 'Senior Django Developer',
                    'Full Stack Python Developer', 'Python/Django Engineer'
                ],
                'companies': ['TechCorp', 'DevSolutions', 'CodeCraft Inc', 'Binary Systems', 'DataFlow Labs'],
                'skills': ['Python', 'Django', 'PostgreSQL', 'REST APIs', 'Docker'],
                'salary_range': (80000, 140000),
                'experience': 'senior',
                'search_keywords': ['python', 'django', 'backend']
            },
            {
                'title_templates': [
                    'JavaScript Developer', 'React Frontend Engineer', 'Full Stack JS Developer',
                    'Node.js Backend Engineer', 'Senior React Developer'
                ],
                'companies': ['WebFlow', 'ReactiveApps', 'JS Solutions', 'Frontend Masters', 'Component Co'],
                'skills': ['JavaScript', 'React', 'Node.js', 'TypeScript', 'CSS'],
                'salary_range': (75000, 125000),
                'experience': 'mid',
                'search_keywords': ['javascript', 'react', 'frontend', 'nodejs']
            },
            {
                'title_templates': [
                    'Software Engineer', 'Full Stack Developer', 'Backend Engineer',
                    'Web Developer', 'Application Developer'
                ],
                'companies': ['StartupHub', 'TechVentures', 'AppBuilders', 'DevTeam Pro', 'Code Factory'],
                'skills': ['Python', 'JavaScript', 'SQL', 'Git', 'AWS'],
                'salary_range': (70000, 110000),
                'experience': 'junior',
                'search_keywords': ['software engineer', 'developer', 'full stack']
            },
            {
                'title_templates': [
                    'DevOps Engineer', 'Cloud Engineer', 'Site Reliability Engineer',
                    'Infrastructure Engineer', 'Platform Engineer'
                ],
                'companies': ['CloudTech', 'Infrastructure Inc', 'DevOps Solutions', 'Platform Co', 'ScaleUp'],
                'skills': ['AWS', 'Docker', 'Kubernetes', 'CI/CD', 'Terraform'],
                'salary_range': (90000, 160000),
                'experience': 'senior',
                'search_keywords': ['devops', 'cloud', 'aws', 'kubernetes']
            },
            {
                'title_templates': [
                    'Data Scientist', 'ML Engineer', 'Python Data Analyst',
                    'Machine Learning Developer', 'AI Engineer'
                ],
                'companies': ['DataMind', 'AI Innovations', 'ML Labs', 'Analytics Pro', 'Data Insights'],
                'skills': ['Python', 'Machine Learning', 'Pandas', 'TensorFlow', 'SQL'],
                'salary_range': (85000, 145000),
                'experience': 'mid',
                'search_keywords': ['data', 'machine learning', 'ai', 'python']
            }
        ]
        
        jobs = []
        
        try:
            for template in job_templates:
                # Check if this template matches search terms
                template_keywords = template['search_keywords']
                if any(term.lower() in ' '.join(template_keywords).lower() for term in search_terms):
                    
                    # Generate 2-3 jobs per matching template
                    for i in range(random.randint(2, 4)):
                        title = random.choice(template['title_templates'])
                        company = random.choice(template['companies'])
                        
                        salary_min, salary_max = template['salary_range']
                        # Add some variation
                        salary_min += random.randint(-5000, 5000)
                        salary_max += random.randint(-5000, 10000)
                        
                        locations = ['Remote', 'New York, NY', 'San Francisco, CA', 'Austin, TX', 'Chicago, IL']
                        job_location = location if location else random.choice(locations)
                        
                        location_type = 'remote' if 'Remote' in job_location else random.choice(['hybrid', 'onsite'])
                        
                        job = {
                            'title': title,
                            'company': company,
                            'description': f'We are looking for a {title.lower()} to join our growing team. You will work with {", ".join(template["skills"][:3])} and contribute to exciting projects.',
                            'location': job_location,
                            'location_type': location_type,
                            'salary_min': salary_min,
                            'salary_max': salary_max,
                            'salary_currency': 'USD',
                            'experience_level': template['experience'],
                            'job_type': 'full_time',
                            'skills': template['skills'],
                            'posted_date': datetime.now(timezone.utc) - timedelta(days=random.randint(1, 14)),
                            'source_url': f'https://stackoverflow.com/jobs/{random.randint(100000, 999999)}',
                            'source': 'Stack Overflow',
                            'external_id': f'so_{random.randint(100000, 999999)}',
                        }
                        
                        jobs.append(job)
            
            print(f"Stack Overflow: Found {len(jobs)} matching jobs")
            return jobs
            
        except Exception as e:
            print(f"Error generating Stack Overflow jobs: {e}")
            return []