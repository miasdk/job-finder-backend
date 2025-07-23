"""
Show My Job Matches - Display AI recommended jobs and those meeting requirements
Quick way to see your best job matches from the command line
"""

from django.core.management.base import BaseCommand
from jobs.models import Job, JobScore


class Command(BaseCommand):
    help = 'Show AI recommended jobs and jobs meeting requirements'

    def add_arguments(self, parser):
        parser.add_argument(
            '--recommended-only',
            action='store_true',
            help='Show only AI recommended jobs',
        )
        parser.add_argument(
            '--requirements-only',
            action='store_true',
            help='Show only jobs meeting requirements',
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('🎯 YOUR JOB MATCHES'))
        self.stdout.write('')
        
        # AI Recommended Jobs
        if not options['requirements_only']:
            recommended_jobs = Job.objects.filter(
                is_active=True,
                score__recommended_for_application=True
            ).select_related('company', 'score').order_by('-score__total_score')
            
            self.stdout.write(self.style.WARNING(f'🔥 AI RECOMMENDED JOBS ({recommended_jobs.count()})'))
            self.stdout.write('These are jobs the AI strongly recommends for you:')
            self.stdout.write('')
            
            if recommended_jobs.exists():
                for i, job in enumerate(recommended_jobs, 1):
                    score = job.score.total_score if job.score else 0
                    salary_info = ""
                    if job.salary_min:
                        salary_info = f" | ${job.salary_min:,}"
                        if job.salary_max:
                            salary_info = f" | ${job.salary_min:,}-${job.salary_max:,}"
                    
                    self.stdout.write(f'  {i}. {job.title}')
                    self.stdout.write(f'     🏢 {job.company.name} | 📍 {job.location} | ⭐ {score:.1f}%{salary_info}')
                    
                    if job.score and job.score.matching_skills:
                        skills = ', '.join(job.score.matching_skills[:5])
                        if len(job.score.matching_skills) > 5:
                            skills += f' +{len(job.score.matching_skills) - 5} more'
                        self.stdout.write(f'     🎯 Skills: {skills}')
                    
                    self.stdout.write(f'     🔗 {job.source_url}')
                    self.stdout.write('')
            else:
                self.stdout.write('     No AI recommended jobs found. Consider updating your preferences.')
                self.stdout.write('')
        
        # Jobs Meeting Requirements
        if not options['recommended_only']:
            meets_requirements = Job.objects.filter(
                is_active=True,
                score__meets_minimum_requirements=True
            ).select_related('company', 'score').order_by('-score__total_score')[:20]  # Limit to top 20
            
            self.stdout.write(self.style.WARNING(f'✅ JOBS MEETING REQUIREMENTS (Top 20 of {Job.objects.filter(is_active=True, score__meets_minimum_requirements=True).count()})'))
            self.stdout.write('Jobs where you meet the basic requirements:')
            self.stdout.write('')
            
            if meets_requirements.exists():
                for i, job in enumerate(meets_requirements, 1):
                    score = job.score.total_score if job.score else 0
                    salary_info = ""
                    if job.salary_min:
                        salary_info = f" | ${job.salary_min:,}"
                        if job.salary_max:
                            salary_info = f" | ${job.salary_min:,}-${job.salary_max:,}"
                    
                    # Color code by score
                    if score >= 70:
                        score_style = self.style.SUCCESS(f'{score:.1f}%')
                    elif score >= 50:
                        score_style = self.style.WARNING(f'{score:.1f}%')
                    else:
                        score_style = f'{score:.1f}%'
                    
                    self.stdout.write(f'  {i}. {job.title}')
                    self.stdout.write(f'     🏢 {job.company.name} | 📍 {job.location} | ⭐ {score_style}{salary_info}')
                    self.stdout.write(f'     🔗 {job.source_url}')
                    self.stdout.write('')
            else:
                self.stdout.write('     No qualifying jobs found. Consider lowering score thresholds.')
                self.stdout.write('')
        
        # Summary and next steps
        if not options['recommended_only'] and not options['requirements_only']:
            total_recommended = Job.objects.filter(is_active=True, score__recommended_for_application=True).count()
            total_qualified = Job.objects.filter(is_active=True, score__meets_minimum_requirements=True).count()
            total_jobs = Job.objects.filter(is_active=True).count()
            
            self.stdout.write(self.style.SUCCESS('📊 SUMMARY'))
            self.stdout.write(f'• AI Recommended: {total_recommended} jobs')
            self.stdout.write(f'• Meets Requirements: {total_qualified} jobs')
            self.stdout.write(f'• Total Active Jobs: {total_jobs} jobs')
            self.stdout.write('')
            
            if total_recommended == 0:
                self.stdout.write(self.style.WARNING('💡 TIPS TO GET MORE RECOMMENDATIONS:'))
                self.stdout.write('• Update your skills in preferences')
                self.stdout.write('• Lower minimum score threshold')
                self.stdout.write('• Add more job titles to search for')
                self.stdout.write('• Run: python manage.py expand_job_sources --min-score 15')
                self.stdout.write('')
            
            self.stdout.write(self.style.SUCCESS('🎯 QUICK ACCESS:'))
            self.stdout.write('• Web UI: http://localhost:3000/jobs?filter=recommended')
            self.stdout.write('• API: http://localhost:8000/api/jobs/recommended/')
            self.stdout.write('• Requirements API: http://localhost:8000/api/jobs/meets-requirements/')
            self.stdout.write('')
            
            self.stdout.write(self.style.SUCCESS('✨ Done! Focus on the AI recommended jobs first!')) 