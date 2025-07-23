import logging
from typing import Dict, List, Optional
from django.utils import timezone
from .models import Job, JobScore, UserPreferences

logger = logging.getLogger('jobs')

class JobScorer:
    """Score jobs based on user's dynamic preferences"""
    
    def __init__(self, preferences: Optional[UserPreferences] = None):
        """Initialize with user preferences or load from database"""
        if preferences is None:
            preferences = UserPreferences.get_active_preferences()
        
        self.preferences = preferences
        self.user_skills = self._build_skills_dict()
        self.location_preferences = self._build_location_preferences()
        self.salary_target = self._build_salary_target()
        self.company_type_preferences = self._build_company_preferences()
        self.experience_preferences = self._build_experience_preferences()
        
        # Scoring weights from preferences
        self.weights = {
            'skills': self.preferences.skills_weight / 100,
            'experience': self.preferences.experience_weight / 100,
            'location': self.preferences.location_weight / 100,
            'salary': self.preferences.salary_weight / 100,
            'company': self.preferences.company_weight / 100
        }
    
    def _build_skills_dict(self) -> Dict[str, float]:
        """Build skills dictionary with equal weights from user preferences"""
        skills_dict = {}
        if self.preferences.skills:
            # Give equal weight to all user skills
            base_weight = 100 / len(self.preferences.skills)
            for skill in self.preferences.skills:
                skills_dict[skill] = base_weight
        return skills_dict
    
    def _build_location_preferences(self) -> Dict[str, float]:
        """Build location preferences from user settings"""
        location_prefs = {}
        
        # Add preferred locations
        for location in self.preferences.preferred_locations:
            if location.lower() == 'remote':
                location_prefs['Remote'] = 10
            else:
                location_prefs[location] = 8
        
        # Add location types with different weights
        for loc_type in self.preferences.location_types:
            if loc_type == 'remote':
                location_prefs['Remote'] = 10
            elif loc_type == 'hybrid':
                location_prefs['Hybrid'] = 8
            elif loc_type == 'onsite':
                # Add bonus for preferred locations if onsite
                for location in self.preferences.preferred_locations:
                    if location.lower() not in ['remote', 'hybrid']:
                        location_prefs[location] = 6
        
        return location_prefs
    
    def _build_salary_target(self) -> Dict[str, int]:
        """Build salary target from user preferences"""
        return {
            'min_acceptable': self.preferences.min_salary,
            'target_min': self.preferences.min_salary,
            'target_max': self.preferences.max_salary,
            'dream': int(self.preferences.max_salary * 1.3)  # 30% above max
        }
    
    def _build_company_preferences(self) -> Dict[str, float]:
        """Build company type preferences"""
        company_prefs = {}
        if self.preferences.preferred_companies:
            base_score = 8
            for company_type in self.preferences.preferred_companies:
                company_prefs[company_type.lower()] = base_score
        
        # Default for unknown companies
        company_prefs['unknown'] = 3
        return company_prefs
    
    def _build_experience_preferences(self) -> Dict[str, float]:
        """Build experience level preferences based on user's target range"""
        exp_prefs = {}
        min_exp = self.preferences.min_experience_years
        max_exp = self.preferences.max_experience_years
        
        # Score experience levels based on user's range
        if 'entry' in self.preferences.experience_levels:
            exp_prefs['entry'] = 15
        if 'junior' in self.preferences.experience_levels:
            exp_prefs['junior'] = 12
        if 'mid' in self.preferences.experience_levels:
            exp_prefs['mid'] = 8
        if 'senior' in self.preferences.experience_levels:
            exp_prefs['senior'] = 5
        else:
            # Penalty for senior if not preferred
            exp_prefs['senior'] = -20
            
        # Defaults for levels not specified
        exp_prefs.setdefault('lead', -30)
        exp_prefs.setdefault('manager', -40)
        
        return exp_prefs
    
    def calculate_skills_score(self, job: Job) -> Dict[str, float]:
        """Calculate skills match score for a job"""
        if not job.required_skills:
            return {'score': 0, 'matching_skills': [], 'missing_skills': []}
        
        matching_skills = []
        total_skill_weight = 0
        matched_weight = 0
        
        # Find matching skills
        for skill in job.required_skills:
            if skill in self.user_skills:
                matching_skills.append(skill)
                weight = self.user_skills[skill]
                matched_weight += weight
                total_skill_weight += weight
            else:
                # Add weight for skills we don't have
                total_skill_weight += 5  # Default weight for unknown skills
        
        # Calculate percentage match
        if total_skill_weight == 0:
            score = 0
        else:
            score = (matched_weight / total_skill_weight) * 100
            
        # Bonus for having many of our primary skills
        primary_skills_matched = sum(1 for skill in matching_skills 
                                   if self.user_skills.get(skill, 0) >= 15)
        score += primary_skills_matched * 5  # Bonus for primary skills
        
        # Cap at 100
        score = min(score, 100)
        
        missing_skills = [skill for skill in job.required_skills 
                         if skill not in matching_skills]
        
        return {
            'score': score,
            'matching_skills': matching_skills,
            'missing_skills': missing_skills
        }
    
    def calculate_experience_score(self, job: Job) -> float:
        """Calculate experience level match score"""
        exp_level = job.experience_level
        base_score = self.experience_preferences.get(exp_level, 0)
        
        # Bonus points for entry-level friendly positions
        if job.is_entry_level_friendly:
            base_score += 10
        
        # Check job title for additional entry-level indicators
        title_lower = job.title.lower()
        entry_keywords = ['entry', 'junior', 'new grad', 'graduate', 'associate']
        if any(keyword in title_lower for keyword in entry_keywords):
            base_score += 5
        
        # Penalty for requiring too much experience
        desc_lower = job.description.lower()
        if '5+ years' in desc_lower or '5 years' in desc_lower:
            base_score -= 20
        if '3+ years' in desc_lower or '3 years' in desc_lower:
            base_score -= 10
        
        return max(0, min(base_score, 100))
    
    def calculate_location_score(self, job: Job) -> float:
        """Calculate location preference score"""
        location_text = f"{job.location} {job.location_type}".lower()
        
        score = 0
        for location, points in self.location_preferences.items():
            if location.lower() in location_text:
                score = max(score, points)
        
        # Special handling for remote/hybrid
        if job.location_type == 'remote':
            score = max(score, self.location_preferences['Remote'])
        elif job.location_type == 'hybrid':
            score = max(score, self.location_preferences['Hybrid'])
        
        return score
    
    def calculate_salary_score(self, job: Job) -> float:
        """Calculate salary match score"""
        if not job.salary_min and not job.salary_max:
            return 5  # Neutral score for unspecified salary
        
        # Use minimum salary if available, otherwise maximum
        salary = job.salary_min if job.salary_min else job.salary_max
        
        if salary < self.salary_target['min_acceptable']:
            return 0  # Below minimum acceptable
        elif salary < self.salary_target['target_min']:
            return 5  # Below target but acceptable
        elif salary <= self.salary_target['target_max']:
            return 10  # Within target range
        elif salary <= self.salary_target['dream']:
            return 15  # Above target
        else:
            return 15  # Dream salary
    
    def calculate_company_score(self, job: Job) -> float:
        """Calculate company type preference score"""
        company_type = job.company.company_type or 'unknown'
        return self.company_type_preferences.get(company_type, 0)
    
    def calculate_total_score(self, job: Job) -> Dict:
        """Calculate total weighted score for a job"""
        
        # Calculate individual scores
        skills_data = self.calculate_skills_score(job)
        skills_score = skills_data['score']
        experience_score = self.calculate_experience_score(job)
        location_score = self.calculate_location_score(job)
        salary_score = self.calculate_salary_score(job)
        company_score = self.calculate_company_score(job)
        
        # Use dynamic weights from user preferences
        # Calculate weighted total
        total_score = (
            skills_score * self.weights['skills'] +
            experience_score * self.weights['experience'] +
            location_score * self.weights['location'] +
            salary_score * self.weights['salary'] +
            company_score * self.weights['company']
        )
        
        # Determine recommendation flags using dynamic thresholds
        min_threshold = self.preferences.min_job_score_threshold
        
        meets_minimum = (
            skills_score >= 30 and  # At least 30% skill match
            experience_score >= 0 and  # Not senior level
            total_score >= min_threshold  # User's minimum score threshold
        )
        
        recommended = total_score >= (min_threshold + 20) and meets_minimum
        
        return {
            'skills_score': skills_score,
            'experience_score': experience_score,
            'location_score': location_score,
            'salary_score': salary_score,
            'company_score': company_score,
            'total_score': total_score,
            'matching_skills': skills_data['matching_skills'],
            'missing_skills': skills_data['missing_skills'],
            'meets_minimum_requirements': meets_minimum,
            'recommended_for_application': recommended
        }
    
    def score_job(self, job: Job) -> JobScore:
        """Score a job and update/create JobScore record"""
        scores = self.calculate_total_score(job)
        
        # Get or create JobScore
        job_score, created = JobScore.objects.get_or_create(
            job=job,
            defaults={
                'skills_match_score': scores['skills_score'],
                'experience_match_score': scores['experience_score'],
                'location_preference_score': scores['location_score'],
                'salary_match_score': scores['salary_score'],
                'company_type_score': scores['company_score'],
                'total_score': scores['total_score'],
                'matching_skills': scores['matching_skills'],
                'missing_skills': scores['missing_skills'],
                'meets_minimum_requirements': scores['meets_minimum_requirements'],
                'recommended_for_application': scores['recommended_for_application']
            }
        )
        
        if not created:
            # Update existing score
            job_score.skills_match_score = scores['skills_score']
            job_score.experience_match_score = scores['experience_score']
            job_score.location_preference_score = scores['location_score']
            job_score.salary_match_score = scores['salary_score']
            job_score.company_type_score = scores['company_score']
            job_score.total_score = scores['total_score']
            job_score.matching_skills = scores['matching_skills']
            job_score.missing_skills = scores['missing_skills']
            job_score.meets_minimum_requirements = scores['meets_minimum_requirements']
            job_score.recommended_for_application = scores['recommended_for_application']
            job_score.save()
        
        logger.info(f"Scored job '{job.title}' with total score: {scores['total_score']:.1f}")
        
        return job_score
    
    def score_all_jobs(self) -> int:
        """Score all unscored jobs"""
        unscored_jobs = Job.objects.filter(
            is_active=True,
            score__isnull=True
        )
        
        scored_count = 0
        for job in unscored_jobs:
            try:
                self.score_job(job)
                scored_count += 1
            except Exception as e:
                logger.error(f"Error scoring job {job.id}: {str(e)}")
        
        logger.info(f"Scored {scored_count} jobs")
        return scored_count
    
    def rescore_all_jobs(self) -> int:
        """Rescore all active jobs"""
        active_jobs = Job.objects.filter(is_active=True)
        
        scored_count = 0
        for job in active_jobs:
            try:
                self.score_job(job)
                scored_count += 1
            except Exception as e:
                logger.error(f"Error rescoring job {job.id}: {str(e)}")
        
        logger.info(f"Rescored {scored_count} jobs")
        return scored_count