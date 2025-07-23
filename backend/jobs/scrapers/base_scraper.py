import logging
import re
from abc import ABC, abstractmethod
from typing import List, Dict, Optional
from datetime import datetime
import requests
from bs4 import BeautifulSoup

logger = logging.getLogger('jobs')

class BaseScraper(ABC):
    """Base class for job scrapers"""
    
    def __init__(self, user_preferences=None):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        
        # Load user preferences if not provided
        if user_preferences is None:
            from ..models import UserPreferences
            user_preferences = UserPreferences.get_active_preferences()
        
        self.user_preferences = user_preferences
    
    @abstractmethod
    def scrape_jobs(self, search_terms: List[str], location: str = "New York, NY") -> List[Dict]:
        """Scrape jobs based on search terms and location"""
        pass
    
    def extract_skills_from_text(self, text: str) -> List[str]:
        """Extract technical skills from job description using user's skill set"""
        # Use user's skills from preferences
        user_skills = self.user_preferences.skills if self.user_preferences.skills else [
            'Python', 'Django', 'PostgreSQL', 'React', 'JavaScript', 'HTML', 'CSS', 'Git'
        ]
        
        found_skills = []
        text_lower = text.lower()
        
        for skill in user_skills:
            # Case-insensitive search with word boundaries
            pattern = rf'\b{re.escape(skill.lower())}\b'
            if re.search(pattern, text_lower):
                found_skills.append(skill)
        
        return found_skills
    
    def get_search_terms(self) -> List[str]:
        """Get search terms from user preferences"""
        terms = []
        
        # Add job titles from preferences
        if self.user_preferences.job_titles:
            terms.extend(self.user_preferences.job_titles)
        
        # Add primary skills as search terms
        if self.user_preferences.skills:
            # Include top skills in search
            primary_skills = self.user_preferences.skills[:3]  # Top 3 skills
            terms.extend(primary_skills)
        
        # Default search terms if none specified
        if not terms:
            terms = ['Python Developer', 'Django Developer', 'Backend Developer']
        
        return terms
    
    def get_locations(self) -> List[str]:
        """Get preferred locations from user preferences"""
        if self.user_preferences.preferred_locations:
            return self.user_preferences.preferred_locations
        return ['New York', 'Remote']
    
    def extract_salary_info(self, text: str) -> Dict[str, Optional[int]]:
        """Extract salary information from job description"""
        salary_patterns = [
            r'\$(\d{1,3}(?:,\d{3})*)\s*-\s*\$(\d{1,3}(?:,\d{3})*)',  # $70,000 - $120,000
            r'\$(\d{1,3}(?:,\d{3})*)\s*to\s*\$(\d{1,3}(?:,\d{3})*)',  # $70,000 to $120,000
            r'(\d{1,3}(?:,\d{3})*)\s*-\s*(\d{1,3}(?:,\d{3})*)\s*k',   # 70-120k
            r'\$(\d{1,3}(?:,\d{3})*)',  # $80,000
            r'(\d{1,3}(?:,\d{3})*)\s*k',  # 80k
        ]
        
        salary_info = {'min': None, 'max': None}
        
        for pattern in salary_patterns:
            matches = re.search(pattern, text, re.IGNORECASE)
            if matches:
                groups = matches.groups()
                if len(groups) == 2:
                    # Range found
                    salary_info['min'] = int(groups[0].replace(',', ''))
                    salary_info['max'] = int(groups[1].replace(',', ''))
                    # Handle k notation
                    if 'k' in text[matches.start():matches.end()].lower():
                        salary_info['min'] *= 1000
                        salary_info['max'] *= 1000
                elif len(groups) == 1:
                    # Single value found
                    value = int(groups[0].replace(',', ''))
                    if 'k' in text[matches.start():matches.end()].lower():
                        value *= 1000
                    salary_info['min'] = value
                break
        
        return salary_info
    
    def determine_experience_level(self, title: str, description: str) -> str:
        """Determine experience level from job title and description"""
        title_lower = title.lower()
        desc_lower = description.lower()
        
        entry_keywords = ['entry', 'junior', 'new grad', 'graduate', 'associate', 'trainee', '0-2 years']
        senior_keywords = ['senior', 'lead', 'principal', 'staff', '5+ years', 'experienced']
        manager_keywords = ['manager', 'director', 'head', 'vp', 'vice president']
        
        combined_text = f"{title_lower} {desc_lower}"
        
        if any(keyword in combined_text for keyword in manager_keywords):
            return 'manager'
        elif any(keyword in combined_text for keyword in senior_keywords):
            return 'senior'
        elif any(keyword in combined_text for keyword in entry_keywords):
            return 'entry'
        else:
            return 'junior'  # Default to junior if unclear
    
    def determine_location_type(self, title: str, description: str, location: str) -> str:
        """Determine if job is remote, hybrid, or onsite"""
        combined_text = f"{title.lower()} {description.lower()} {location.lower()}"
        
        if any(keyword in combined_text for keyword in ['remote', 'work from home', 'wfh', 'distributed']):
            return 'remote'
        elif any(keyword in combined_text for keyword in ['hybrid', 'flexible', 'remote/onsite']):
            return 'hybrid'
        else:
            return 'onsite'
    
    def clean_text(self, text: str) -> str:
        """Clean and normalize text"""
        if not text:
            return ""
        
        # Remove HTML tags if present
        soup = BeautifulSoup(text, 'html.parser')
        text = soup.get_text()
        
        # Normalize whitespace
        text = ' '.join(text.split())
        
        return text.strip()