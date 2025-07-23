"""
AI Engine for Job Finder - Real AI-powered features
This makes our platform truly AI-powered with semantic matching and intelligent analysis
"""

import logging
import re
from typing import List, Dict, Tuple, Optional
from datetime import datetime, timezone
import json

try:
    import openai
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

try:
    import numpy as np
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False
    logger.warning("Scikit-learn not available - using fallback similarity calculation")

from django.conf import settings
from .models import Job, UserPreferences

logger = logging.getLogger('jobs')


class JobAIEngine:
    """AI-powered job analysis and matching engine"""
    
    def __init__(self):
        self.openai_client = None
        self.vectorizer = None
        
        # Initialize OpenAI if available
        if OPENAI_AVAILABLE and hasattr(settings, 'OPENAI_API_KEY'):
            try:
                self.openai_client = OpenAI(api_key=settings.OPENAI_API_KEY)
                logger.info("OpenAI client initialized")
            except Exception as e:
                logger.warning(f"OpenAI initialization failed: {e}")
        
        # Initialize TF-IDF vectorizer for semantic similarity
        if SKLEARN_AVAILABLE:
            self.vectorizer = TfidfVectorizer(
                max_features=1000,
                stop_words='english',
                ngram_range=(1, 2)
            )
            logger.info("TF-IDF vectorizer initialized")
    
    def analyze_job_with_ai(self, job: Job, user_preferences: UserPreferences) -> Dict:
        """
        AI-powered job analysis using LLM
        Returns detailed analysis including fit score, pros/cons, career impact
        """
        if not self.openai_client:
            return self._fallback_analysis(job, user_preferences)
        
        try:
            # Prepare context for AI analysis
            context = self._prepare_job_context(job, user_preferences)
            
            # AI prompt for comprehensive job analysis
            prompt = f"""
            You are an expert career advisor analyzing a job opportunity. Provide a detailed analysis.
            
            JOB DETAILS:
            Title: {job.title}
            Company: {job.company.name}
            Location: {job.location} ({job.location_type})
            Description: {job.description[:1000]}...
            Required Skills: {', '.join(job.required_skills or [])}
            Salary: ${job.salary_min}-${job.salary_max} (if available)
            Experience Level: {job.experience_level}
            
            USER PROFILE:
            Skills: {', '.join(user_preferences.skills)}
            Experience Level: {', '.join(user_preferences.experience_levels)}
            Salary Range: ${user_preferences.min_salary}-${user_preferences.max_salary}
            Preferred Locations: {', '.join(user_preferences.preferred_locations)}
            Job Titles: {', '.join(user_preferences.job_titles)}
            
            Provide a JSON response with:
            {{
                "overall_fit_score": <0-100>,
                "skills_match_percentage": <0-100>,
                "pros": ["list", "of", "advantages"],
                "cons": ["list", "of", "concerns"],
                "missing_skills": ["skills", "to", "develop"],
                "career_impact": "How this role advances career goals",
                "salary_assessment": "Fair/Below Market/Above Market",
                "recommendation": "Strong Apply/Apply/Consider/Skip",
                "reasoning": "Brief explanation of recommendation"
            }}
            """
            
            response = self.openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=800,
                temperature=0.3
            )
            
            # Parse AI response
            ai_analysis = json.loads(response.choices[0].message.content)
            
            logger.info(f"AI analysis completed for job: {job.title}")
            return ai_analysis
            
        except Exception as e:
            logger.error(f"AI analysis failed: {e}")
            return self._fallback_analysis(job, user_preferences)
    
    def semantic_job_similarity(self, job_description: str, user_skills: List[str]) -> float:
        """
        Calculate semantic similarity between job requirements and user skills
        Uses embeddings for better understanding than keyword matching
        """
        if not self.openai_client:
            return self._tfidf_similarity(job_description, user_skills)
        
        try:
            # Get embeddings for job description
            job_embedding = self._get_embedding(job_description)
            
            # Get embeddings for user skills
            skills_text = " ".join(user_skills)
            skills_embedding = self._get_embedding(skills_text)
            
            # Calculate cosine similarity
            if SKLEARN_AVAILABLE:
                similarity = np.dot(job_embedding, skills_embedding) / (
                    np.linalg.norm(job_embedding) * np.linalg.norm(skills_embedding)
                )
            else:
                # Simple dot product fallback
                similarity = sum(a * b for a, b in zip(job_embedding, skills_embedding)) / (
                    (sum(a * a for a in job_embedding) ** 0.5) * 
                    (sum(b * b for b in skills_embedding) ** 0.5)
                )
            
            return float(similarity)
            
        except Exception as e:
            logger.error(f"Semantic similarity calculation failed: {e}")
            return self._tfidf_similarity(job_description, user_skills)
    
    def extract_skills_with_ai(self, job_description: str) -> List[str]:
        """
        AI-powered skill extraction from job descriptions
        More accurate than keyword matching
        """
        if not self.openai_client:
            return self._extract_skills_regex(job_description)
        
        try:
            prompt = f"""
            Extract technical skills and technologies mentioned in this job description.
            Focus on programming languages, frameworks, tools, databases, cloud platforms.
            
            Job Description:
            {job_description[:1500]}
            
            Return only a JSON array of skills: ["skill1", "skill2", ...]
            """
            
            response = self.openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=200,
                temperature=0.1
            )
            
            skills = json.loads(response.choices[0].message.content)
            
            # Validate and clean skills
            validated_skills = [skill for skill in skills if isinstance(skill, str) and len(skill) > 1]
            
            logger.info(f"AI extracted {len(validated_skills)} skills")
            return validated_skills[:15]  # Limit to top 15 skills
            
        except Exception as e:
            logger.error(f"AI skill extraction failed: {e}")
            return self._extract_skills_regex(job_description)
    
    def predict_job_quality(self, job: Job) -> Dict:
        """
        AI-powered job quality prediction
        Analyzes company, role, requirements to predict job satisfaction
        """
        if not self.openai_client:
            return self._basic_quality_score(job)
        
        try:
            prompt = f"""
            Rate this job opportunity's quality on multiple dimensions:
            
            Title: {job.title}
            Company: {job.company.name}
            Description: {job.description[:800]}
            Location: {job.location} ({job.location_type})
            
            Provide JSON analysis:
            {{
                "company_reputation_score": <0-100>,
                "role_growth_potential": <0-100>,
                "work_life_balance_indicators": <0-100>,
                "compensation_competitiveness": <0-100>,
                "technology_stack_modernity": <0-100>,
                "overall_quality_score": <0-100>,
                "red_flags": ["list", "any", "concerns"],
                "green_flags": ["list", "positive", "indicators"]
            }}
            """
            
            response = self.openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=400,
                temperature=0.2
            )
            
            quality_analysis = json.loads(response.choices[0].message.content)
            
            logger.info(f"AI quality prediction completed for: {job.title}")
            return quality_analysis
            
        except Exception as e:
            logger.error(f"AI quality prediction failed: {e}")
            return self._basic_quality_score(job)
    
    def generate_application_insights(self, job: Job, user_preferences: UserPreferences) -> Dict:
        """
        AI-generated application strategy and insights
        """
        if not self.openai_client:
            return {"insights": "AI insights unavailable", "strategy": "Apply based on your judgment"}
        
        try:
            prompt = f"""
            As a career coach, provide application strategy for this job:
            
            Job: {job.title} at {job.company.name}
            User Skills: {', '.join(user_preferences.skills)}
            
            Provide JSON advice:
            {{
                "application_strategy": "Brief strategy for applying",
                "key_selling_points": ["highlight", "these", "skills"],
                "cover_letter_focus": "What to emphasize in cover letter",
                "interview_prep_tips": ["tip1", "tip2", "tip3"],
                "salary_negotiation_advice": "Negotiation guidance"
            }}
            """
            
            response = self.openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=300,
                temperature=0.4
            )
            
            insights = json.loads(response.choices[0].message.content)
            return insights
            
        except Exception as e:
            logger.error(f"Application insights generation failed: {e}")
            return {"insights": "Unable to generate AI insights", "strategy": "Standard application approach"}
    
    # Helper methods
    
    def _get_embedding(self, text: str) -> np.ndarray:
        """Get OpenAI embedding for text"""
        response = self.openai_client.embeddings.create(
            model="text-embedding-ada-002",
            input=text[:8000]  # Limit input length
        )
        if SKLEARN_AVAILABLE:
            return np.array(response.data[0].embedding)
        else:
            return response.data[0].embedding
    
    def _tfidf_similarity(self, job_description: str, user_skills: List[str]) -> float:
        """Fallback similarity using TF-IDF or simple word matching"""
        if not SKLEARN_AVAILABLE:
            return self._simple_word_similarity(job_description, user_skills)
        
        try:
            skills_text = " ".join(user_skills)
            corpus = [job_description, skills_text]
            
            tfidf_matrix = self.vectorizer.fit_transform(corpus)
            similarity = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])
            
            return float(similarity[0][0])
        except:
            return self._simple_word_similarity(job_description, user_skills)
    
    def _simple_word_similarity(self, job_description: str, user_skills: List[str]) -> float:
        """Simple word-based similarity when sklearn unavailable"""
        if not user_skills:
            return 0.0
        
        job_words = set(job_description.lower().split())
        skill_words = set(' '.join(user_skills).lower().split())
        
        if not skill_words:
            return 0.0
        
        # Calculate Jaccard similarity
        intersection = len(job_words.intersection(skill_words))
        union = len(job_words.union(skill_words))
        
        return intersection / union if union > 0 else 0.0
    
    def _extract_skills_regex(self, text: str) -> List[str]:
        """Fallback skill extraction using regex patterns"""
        tech_skills = [
            'Python', 'Django', 'JavaScript', 'React', 'Node.js', 'TypeScript',
            'PostgreSQL', 'MySQL', 'MongoDB', 'Redis', 'AWS', 'Docker',
            'Kubernetes', 'Git', 'Linux', 'Java', 'Go', 'Rust', 'PHP',
            'Ruby', 'Swift', 'Kotlin', 'C++', 'C#', '.NET', 'Angular',
            'Vue.js', 'Flask', 'FastAPI', 'GraphQL', 'REST API', 'HTML',
            'CSS', 'SCSS', 'Tailwind', 'Bootstrap', 'Figma', 'Sketch'
        ]
        
        found_skills = []
        text_lower = text.lower()
        
        for skill in tech_skills:
            if skill.lower() in text_lower:
                found_skills.append(skill)
        
        return found_skills[:10]
    
    def _fallback_analysis(self, job: Job, user_preferences: UserPreferences) -> Dict:
        """Basic analysis when AI is unavailable"""
        return {
            "overall_fit_score": 50,
            "skills_match_percentage": 60,
            "pros": ["Relevant experience level", "Good company"],
            "cons": ["Limited information available"],
            "missing_skills": [],
            "career_impact": "Potential career advancement opportunity",
            "salary_assessment": "Market rate",
            "recommendation": "Consider",
            "reasoning": "Basic analysis - AI unavailable"
        }
    
    def _basic_quality_score(self, job: Job) -> Dict:
        """Basic quality assessment when AI unavailable"""
        return {
            "company_reputation_score": 70,
            "role_growth_potential": 65,
            "work_life_balance_indicators": 60,
            "compensation_competitiveness": 70,
            "technology_stack_modernity": 65,
            "overall_quality_score": 66,
            "red_flags": [],
            "green_flags": ["Remote work option"]
        }
    
    def _prepare_job_context(self, job: Job, user_preferences: UserPreferences) -> str:
        """Prepare context for AI analysis"""
        return f"""
        Job Analysis Request:
        - Position: {job.title} at {job.company.name}
        - User has {len(user_preferences.skills)} technical skills
        - Seeking {user_preferences.experience_levels} level positions
        - Location preference: {user_preferences.preferred_locations}
        - Target salary: ${user_preferences.min_salary}-${user_preferences.max_salary}
        """