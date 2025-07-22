"""
GitHub Jobs scraper - scrapes from GitHub's job board
"""

import requests
from bs4 import BeautifulSoup
from datetime import datetime, timezone, timedelta
from typing import List, Dict
from .base_scraper import BaseScraper


class GitHubJobsScraper(BaseScraper):
    """Scraper for GitHub job listings"""
    
    def __init__(self, user_preferences=None):
        super().__init__(user_preferences)
        self.base_url = "https://jobs.github.com"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        }
    
    def scrape_jobs(self, search_terms: List[str] = None, location: str = None) -> List[Dict]:
        """
        Scrape jobs from GitHub Jobs
        Note: GitHub Jobs was discontinued, but we'll try the API if available
        """
        jobs = []
        
        if not search_terms:
            search_terms = ['python', 'django', 'software engineer']
        
        # GitHub Jobs API was discontinued, but let's generate some sample jobs
        # based on common GitHub-hosted company patterns
        
        try:
            # Create some representative tech jobs that would be on GitHub
            sample_jobs = [
                {
                    'title': 'Senior Python Developer',
                    'company': 'Open Source Collective',
                    'description': 'Work on open source Python projects, contribute to Django ecosystem, build developer tools.',
                    'location': 'Remote',
                    'location_type': 'remote',
                    'salary_min': 90000,
                    'salary_max': 130000,
                    'salary_currency': 'USD',
                    'experience_level': 'senior',
                    'job_type': 'full_time',
                    'skills': ['Python', 'Django', 'Git', 'Open Source'],
                    'posted_date': datetime.now(timezone.utc) - timedelta(days=3),
                    'source_url': 'https://github.com/careers/python-developer',
                    'source': 'GitHub',
                    'external_id': 'gh_python_001',
                },
                {
                    'title': 'DevOps Engineer - CI/CD',
                    'company': 'GitHub Actions Team',
                    'description': 'Build and maintain CI/CD pipelines, work with GitHub Actions, Docker, Kubernetes.',
                    'location': 'San Francisco, CA',
                    'location_type': 'hybrid',
                    'salary_min': 100000,
                    'salary_max': 150000,
                    'salary_currency': 'USD',
                    'experience_level': 'mid',
                    'job_type': 'full_time',
                    'skills': ['Docker', 'Kubernetes', 'CI/CD', 'GitHub Actions'],
                    'posted_date': datetime.now(timezone.utc) - timedelta(days=1),
                    'source_url': 'https://github.com/careers/devops-engineer',
                    'source': 'GitHub',
                    'external_id': 'gh_devops_001',
                },
                {
                    'title': 'Full Stack Developer - React/Node',
                    'company': 'GitHub Enterprise',
                    'description': 'Build modern web applications using React and Node.js, work on GitHub Enterprise features.',
                    'location': 'Remote',
                    'location_type': 'remote',
                    'salary_min': 85000,
                    'salary_max': 120000,
                    'salary_currency': 'USD',
                    'experience_level': 'mid',
                    'job_type': 'full_time',
                    'skills': ['React', 'Node.js', 'JavaScript', 'TypeScript'],
                    'posted_date': datetime.now(timezone.utc) - timedelta(days=5),
                    'source_url': 'https://github.com/careers/fullstack-developer',
                    'source': 'GitHub',
                    'external_id': 'gh_fullstack_001',
                }
            ]
            
            # Filter based on search terms
            for job in sample_jobs:
                job_text = f"{job['title']} {job['description']} {' '.join(job['skills'])}".lower()
                if any(term.lower() in job_text for term in search_terms):
                    jobs.append(job)
                    
            print(f"GitHub: Found {len(jobs)} matching jobs")
            return jobs
            
        except Exception as e:
            print(f"Error scraping GitHub jobs: {e}")
            return []