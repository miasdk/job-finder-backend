from django.db import models
from django.utils import timezone

class Company(models.Model):
    name = models.CharField(max_length=200)
    website = models.URLField(blank=True, null=True)
    industry = models.CharField(max_length=100, blank=True)
    location = models.CharField(max_length=200, blank=True)
    company_size = models.CharField(max_length=50, blank=True)
    company_type = models.CharField(max_length=50, blank=True)  # startup, tech, healthcare, fintech
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name_plural = "Companies"
        
    def __str__(self):
        return self.name

class Job(models.Model):
    EMPLOYMENT_TYPES = [
        ('full_time', 'Full-time'),
        ('part_time', 'Part-time'),
        ('contract', 'Contract'),
        ('contract_to_hire', 'Contract-to-hire'),
        ('internship', 'Internship'),
        ('temporary', 'Temporary'),
    ]
    
    EXPERIENCE_LEVELS = [
        ('entry', 'Entry Level'),
        ('junior', 'Junior'),
        ('mid', 'Mid Level'),
        ('senior', 'Senior'),
        ('lead', 'Lead'),
        ('manager', 'Manager'),
    ]
    
    LOCATION_TYPES = [
        ('remote', 'Remote'),
        ('onsite', 'On-site'),
        ('hybrid', 'Hybrid'),
    ]
    
    # Basic Information
    title = models.CharField(max_length=300)
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='jobs')
    description = models.TextField()
    requirements = models.TextField(blank=True)
    benefits = models.TextField(blank=True)
    
    # Location & Work Type
    location = models.CharField(max_length=200)
    location_type = models.CharField(max_length=20, choices=LOCATION_TYPES, default='onsite')
    
    # Employment Details
    employment_type = models.CharField(max_length=20, choices=EMPLOYMENT_TYPES, default='full_time')
    experience_level = models.CharField(max_length=20, choices=EXPERIENCE_LEVELS, default='entry')
    
    # Salary Information
    salary_min = models.IntegerField(null=True, blank=True)
    salary_max = models.IntegerField(null=True, blank=True)
    salary_currency = models.CharField(max_length=10, default='USD')
    
    # Source Information
    source = models.CharField(max_length=100)  # indeed, stackoverflow, angellist, etc
    source_url = models.URLField(unique=True)
    source_job_id = models.CharField(max_length=200, blank=True)
    
    # Skills & Keywords
    required_skills = models.JSONField(default=list)  # ['Python', 'Django', 'PostgreSQL']
    preferred_skills = models.JSONField(default=list)
    keywords = models.JSONField(default=list)  # extracted keywords for matching
    
    # Metadata
    posted_date = models.DateTimeField(null=True, blank=True)
    scraped_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    
    # Additional flags
    is_entry_level_friendly = models.BooleanField(default=False)
    requires_degree = models.BooleanField(default=False)
    offers_visa_sponsorship = models.BooleanField(default=False)
    
    class Meta:
        ordering = ['-posted_date', '-scraped_at']
        indexes = [
            models.Index(fields=['source', 'scraped_at']),
            models.Index(fields=['location_type']),
            models.Index(fields=['experience_level']),
            models.Index(fields=['is_active']),
        ]
    
    def __str__(self):
        return f"{self.title} at {self.company.name}"
    
    @property
    def salary_range_str(self):
        if self.salary_min and self.salary_max:
            return f"${self.salary_min:,} - ${self.salary_max:,}"
        elif self.salary_min:
            return f"${self.salary_min:,}+"
        elif self.salary_max:
            return f"Up to ${self.salary_max:,}"
        return "Salary not specified"

class JobScore(models.Model):
    job = models.OneToOneField(Job, on_delete=models.CASCADE, related_name='score')
    
    # Score Components (0-100 each)
    skills_match_score = models.FloatField(default=0)
    experience_match_score = models.FloatField(default=0)
    location_preference_score = models.FloatField(default=0)
    salary_match_score = models.FloatField(default=0)
    company_type_score = models.FloatField(default=0)
    
    # Overall score (weighted combination)
    total_score = models.FloatField(default=0)
    
    # Matched skills for display
    matching_skills = models.JSONField(default=list)
    missing_skills = models.JSONField(default=list)
    
    # Flags for filtering
    meets_minimum_requirements = models.BooleanField(default=False)
    recommended_for_application = models.BooleanField(default=False)
    
    # Metadata
    scored_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-total_score']
        indexes = [
            models.Index(fields=['total_score']),
            models.Index(fields=['recommended_for_application']),
        ]
    
    def __str__(self):
        return f"Score {self.total_score:.1f} for {self.job.title}"

class EmailDigest(models.Model):
    sent_at = models.DateTimeField(auto_now_add=True)
    recipient_email = models.EmailField()
    subject = models.CharField(max_length=200)
    jobs_included = models.ManyToManyField(Job, related_name='email_digests')
    jobs_count = models.IntegerField(default=0)
    top_score = models.FloatField(default=0)
    email_sent_successfully = models.BooleanField(default=False)
    
    class Meta:
        ordering = ['-sent_at']
    
    def __str__(self):
        return f"Email digest sent on {self.sent_at.strftime('%Y-%m-%d %H:%M')} ({self.jobs_count} jobs)"


class UserPreferences(models.Model):
    # Personal Info
    name = models.CharField(max_length=100, default="Mia Elena")
    email = models.EmailField(default="miariccidev@gmail.com")
    
    # Skills (stored as JSON array)
    skills = models.JSONField(default=list, help_text="List of technical skills")
    
    # Experience Preferences
    experience_levels = models.JSONField(
        default=list, 
        help_text="Preferred experience levels: entry, junior, mid, senior"
    )
    min_experience_years = models.IntegerField(default=0)
    max_experience_years = models.IntegerField(default=3)
    
    # Location Preferences
    preferred_locations = models.JSONField(
        default=list,
        help_text="List of preferred locations/cities"
    )
    location_types = models.JSONField(
        default=list,
        help_text="Preferred work types: remote, hybrid, onsite"
    )
    
    # Salary Preferences
    min_salary = models.IntegerField(default=70000)
    max_salary = models.IntegerField(default=120000)
    currency = models.CharField(max_length=3, default="USD")
    
    # Job Preferences
    job_titles = models.JSONField(
        default=list,
        help_text="Target job titles to search for"
    )
    preferred_companies = models.JSONField(
        default=list,
        help_text="Preferred company types: startup, enterprise, tech, etc."
    )
    
    # Scoring Weights (should add up to 100)
    skills_weight = models.FloatField(default=45.0, help_text="Weight for skills matching (0-100)")
    experience_weight = models.FloatField(default=25.0, help_text="Weight for experience matching (0-100)")
    location_weight = models.FloatField(default=15.0, help_text="Weight for location preference (0-100)")
    salary_weight = models.FloatField(default=10.0, help_text="Weight for salary matching (0-100)")
    company_weight = models.FloatField(default=5.0, help_text="Weight for company type (0-100)")
    
    # Email Settings
    email_enabled = models.BooleanField(default=True)
    email_frequency = models.CharField(
        max_length=20, 
        choices=[
            ('daily', 'Daily'),
            ('weekly', 'Weekly'),
            ('bi_weekly', 'Bi-weekly')
        ],
        default='daily'
    )
    email_time = models.TimeField(default='19:00', help_text="Time to send daily emails (EST)")
    
    # Scraping Settings
    auto_scrape_enabled = models.BooleanField(default=True)
    scrape_frequency_hours = models.IntegerField(default=24, help_text="Hours between scraping runs")
    min_job_score_threshold = models.FloatField(default=50.0, help_text="Only save jobs above this score")
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        ordering = ['-updated_at']
        verbose_name = "User Preferences"
        verbose_name_plural = "User Preferences"
    
    def __str__(self):
        return f"Preferences for {self.name} ({self.email})"
    
    @classmethod
    def get_active_preferences(cls):
        """Get the active user preferences, create default if none exist"""
        prefs = cls.objects.filter(is_active=True).first()
        if not prefs:
            prefs = cls.objects.create(
                skills=[
                    "Python", "Django", "PostgreSQL", "React", "JavaScript", 
                    "HTML", "CSS", "Git", "AWS", "Docker", "REST APIs"
                ],
                experience_levels=["entry", "junior"],
                preferred_locations=["New York", "Remote", "Brooklyn", "Manhattan"],
                location_types=["remote", "hybrid", "onsite"],
                job_titles=[
                    "Python Developer", "Django Developer", "Backend Developer", 
                    "Full Stack Developer", "Junior Software Engineer", 
                    "Entry Level Developer", "Web Developer"
                ],
                preferred_companies=["startup", "tech", "healthcare", "fintech"]
            )
        return prefs
    
    def save(self, *args, **kwargs):
        """Override save to trigger job refresh when preferences change"""
        # Check if this is an update to existing preferences
        is_update = self.pk is not None
        
        super().save(*args, **kwargs)
        
        # Trigger job refresh if preferences were updated and auto-scraping is enabled
        if is_update and self.auto_scrape_enabled:
            try:
                # Import here to avoid circular imports
                from .tasks_enhanced import user_preference_trigger_task
                user_preference_trigger_task.delay()
            except (ImportError, Exception) as e:
                # Fallback if enhanced tasks not available or Redis not configured
                import logging
                logger = logging.getLogger(__name__)
                logger.warning(f"Could not trigger background job rescoring: {e}")
                pass
