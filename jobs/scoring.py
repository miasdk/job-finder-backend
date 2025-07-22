import logging
from typing import Dict, List, Optional
from django.utils import timezone
from .models import Job, JobScore

logger = logging.getLogger('jobs')

class JobScorer:
    """Score jobs based on user's skills and preferences"""
    
    def __init__(self):
        # User's profile from requirements
        self.user_skills = {
            # Primary skills (higher weight)
            'Python': 20,
            'Django': 20,
            'PostgreSQL': 15,
            'React': 15,
            'Django REST Framework': 18,
            
            # Secondary skills (medium weight)
            'TypeScript': 10,
            'JavaScript': 10,
            'Node.js': 12,
            'Express': 10,
            'AWS': 12,
            'Docker': 12,
            'Git': 8,
            'CI/CD': 10,
            
            # Additional skills (lower weight)
            'HTML': 5,
            'CSS': 5,
            'TailwindCSS': 8,
            'Jest': 8,
            'OAuth': 8,
            'Pandas': 10,
            'NumPy': 8,
            'Flask': 12,
            'Celery': 10,
            'Redis': 10,
            'Firebase': 8,
            'SQL': 12,
            'MongoDB': 10,
            'REST API': 12,
            'GraphQL': 8,
            'Linux': 8,
            'Kubernetes': 10
        }
        
        self.location_preferences = {
            'New York': 5,
            'NYC': 5,
            'Manhattan': 5,
            'Brooklyn': 4,
            'Queens': 4,
            'Bronx': 3,
            'Staten Island': 2,
            'Jersey City': 3,
            'Hoboken': 3,
            'Remote': 8,
            'Hybrid': 6
        }
        
        self.salary_target = {
            'min_acceptable': 70000,
            'target_min': 80000,
            'target_max': 120000,
            'dream': 150000
        }
        
        self.company_type_preferences = {
            'startup': 8,
            'tech': 5,
            'healthcare': 7,
            'fintech': 7,
            'unknown': 0
        }
        
        self.experience_preferences = {
            'entry': 15,
            'junior': 12,
            'mid': 5,
            'senior': -30,  # Negative score for senior positions
            'lead': -50,
            'manager': -50
        }
    
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
        
        # Weights for different components
        weights = {
            'skills': 0.45,      # 45% - Most important
            'experience': 0.25,   # 25% - Very important for entry-level
            'location': 0.15,     # 15%
            'salary': 0.10,       # 10%
            'company': 0.05       # 5%
        }
        
        # Calculate weighted total
        total_score = (
            skills_score * weights['skills'] +
            experience_score * weights['experience'] +
            location_score * weights['location'] +
            salary_score * weights['salary'] +
            company_score * weights['company']
        )
        
        # Determine recommendation flags
        meets_minimum = (
            skills_score >= 30 and  # At least 30% skill match
            experience_score >= 0 and  # Not senior level
            total_score >= 40  # Minimum total score
        )
        
        recommended = total_score >= 70 and meets_minimum
        
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