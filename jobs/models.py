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
