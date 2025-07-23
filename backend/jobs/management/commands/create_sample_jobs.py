from django.core.management.base import BaseCommand
from django.utils import timezone
from jobs.models import Job, Company, JobScore
from datetime import datetime, timedelta

class Command(BaseCommand):
    help = 'Create sample jobs for testing'

    def handle(self, *args, **options):
        # Create sample companies
        companies_data = [
            {'name': 'TechStartup Inc', 'company_type': 'startup', 'location': 'New York, NY'},
            {'name': 'Healthcare Solutions', 'company_type': 'healthcare', 'location': 'Brooklyn, NY'},
            {'name': 'FinTech Corp', 'company_type': 'fintech', 'location': 'Manhattan, NY'},
            {'name': 'Remote First Co', 'company_type': 'tech', 'location': 'Remote'},
        ]
        
        companies = []
        for company_data in companies_data:
            company, created = Company.objects.get_or_create(
                name=company_data['name'],
                defaults=company_data
            )
            companies.append(company)
            if created:
                self.stdout.write(f"Created company: {company.name}")
        
        # Create sample jobs
        sample_jobs = [
            {
                'title': 'Junior Python Developer',
                'company': companies[0],
                'description': 'We are looking for a junior Python developer with Django experience. No prior work experience required. Training provided. Must know Python, Django, and basic SQL.',
                'location': 'New York, NY',
                'location_type': 'hybrid',
                'employment_type': 'full_time',
                'experience_level': 'junior',
                'required_skills': ['Python', 'Django', 'SQL'],
                'salary_min': 75000,
                'salary_max': 95000,
                'source': 'test',
                'source_url': 'https://example.com/job1',
                'is_entry_level_friendly': True,
            },
            {
                'title': 'Full Stack Developer',
                'company': companies[1],
                'description': 'Healthcare tech company seeking full stack developer with React and Python experience. Must have Django REST Framework and PostgreSQL knowledge.',
                'location': 'Brooklyn, NY',
                'location_type': 'onsite',
                'employment_type': 'full_time',
                'experience_level': 'entry',
                'required_skills': ['Python', 'Django', 'React', 'PostgreSQL', 'Django REST Framework'],
                'salary_min': 85000,
                'salary_max': 110000,
                'source': 'test',
                'source_url': 'https://example.com/job2',
                'is_entry_level_friendly': True,
            },
            {
                'title': 'Senior Backend Engineer',
                'company': companies[2],
                'description': 'Senior position requiring 5+ years experience with Python, Django, and AWS. FinTech experience preferred.',
                'location': 'Manhattan, NY',
                'location_type': 'onsite',
                'employment_type': 'full_time',
                'experience_level': 'senior',
                'required_skills': ['Python', 'Django', 'AWS', 'PostgreSQL', 'Redis'],
                'salary_min': 130000,
                'salary_max': 170000,
                'source': 'test',
                'source_url': 'https://example.com/job3',
                'is_entry_level_friendly': False,
            },
            {
                'title': 'Remote Python Developer',
                'company': companies[3],
                'description': 'Remote position for Python developer. Experience with Django, React, and modern web development. Entry-level candidates welcome.',
                'location': 'Remote',
                'location_type': 'remote',
                'employment_type': 'full_time',
                'experience_level': 'entry',
                'required_skills': ['Python', 'Django', 'React', 'JavaScript', 'Git'],
                'salary_min': 80000,
                'salary_max': 120000,
                'source': 'test',
                'source_url': 'https://example.com/job4',
                'is_entry_level_friendly': True,
            },
            {
                'title': 'Django Developer - Entry Level',
                'company': companies[0],
                'description': 'Perfect for new graduates! We provide mentorship and training. Need basic Python and Django knowledge. PostgreSQL and React experience is a plus.',
                'location': 'New York, NY',
                'location_type': 'hybrid',
                'employment_type': 'full_time',
                'experience_level': 'entry',
                'required_skills': ['Python', 'Django', 'PostgreSQL', 'React', 'HTML', 'CSS'],
                'salary_min': 70000,
                'salary_max': 90000,
                'source': 'test',
                'source_url': 'https://example.com/job5',
                'is_entry_level_friendly': True,
            }
        ]
        
        created_count = 0
        for job_data in sample_jobs:
            # Check if job already exists
            if Job.objects.filter(source_url=job_data['source_url']).exists():
                continue
            
            job = Job.objects.create(
                **job_data,
                posted_date=timezone.now() - timedelta(days=1)
            )
            
            created_count += 1
            self.stdout.write(f"Created job: {job.title} at {job.company.name}")
        
        self.stdout.write(
            self.style.SUCCESS(f"Successfully created {created_count} sample jobs")
        )