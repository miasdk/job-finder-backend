from django.core.management.base import BaseCommand
from jobs.models import Job, JobScore
from jobs.scoring import JobScorer

class Command(BaseCommand):
    help = 'Score jobs based on user preferences'

    def add_arguments(self, parser):
        parser.add_argument(
            '--rescore',
            action='store_true',
            help='Rescore all jobs, not just unscored ones'
        )
        parser.add_argument(
            '--job-id',
            type=int,
            help='Score a specific job by ID'
        )

    def handle(self, *args, **options):
        scorer = JobScorer()
        
        if options.get('job_id'):
            # Score specific job
            try:
                job = Job.objects.get(id=options['job_id'])
                job_score = scorer.score_job(job)
                self.stdout.write(
                    self.style.SUCCESS(
                        f"Scored job '{job.title}': {job_score.total_score:.1f}/100"
                    )
                )
                return
            except Job.DoesNotExist:
                self.stdout.write(
                    self.style.ERROR(f"Job with ID {options['job_id']} not found")
                )
                return
        
        # Score multiple jobs
        if options.get('rescore'):
            self.stdout.write("Rescoring all active jobs...")
            count = scorer.rescore_all_jobs()
        else:
            self.stdout.write("Scoring unscored jobs...")
            count = scorer.score_all_jobs()
        
        self.stdout.write(
            self.style.SUCCESS(f"Successfully scored {count} jobs")
        )
        
        # Show top scored jobs
        top_jobs = JobScore.objects.filter(
            job__is_active=True
        ).select_related('job', 'job__company').order_by('-total_score')[:5]
        
        if top_jobs:
            self.stdout.write("\nTop 5 scored jobs:")
            for job_score in top_jobs:
                job = job_score.job
                self.stdout.write(
                    f"  {job_score.total_score:.1f} - {job.title} at {job.company.name}"
                )
                if job_score.matching_skills:
                    self.stdout.write(f"    Skills: {', '.join(job_score.matching_skills[:5])}")
        
        # Show recommendation stats
        recommended_count = JobScore.objects.filter(
            job__is_active=True,
            recommended_for_application=True
        ).count()
        
        meets_minimum_count = JobScore.objects.filter(
            job__is_active=True,
            meets_minimum_requirements=True
        ).count()
        
        self.stdout.write(
            f"\nRecommendation stats:"
        )
        self.stdout.write(
            f"  Jobs recommended for application: {recommended_count}"
        )
        self.stdout.write(
            f"  Jobs meeting minimum requirements: {meets_minimum_count}"
        )