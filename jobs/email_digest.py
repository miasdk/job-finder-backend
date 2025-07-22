import logging
from datetime import datetime, timedelta
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils import timezone
from django.conf import settings
from .models import Job, JobScore, EmailDigest

logger = logging.getLogger('jobs')

class EmailDigestManager:
    """Manage daily email digests of job matches"""
    
    def __init__(self):
        self.recipient_email = settings.EMAIL_HOST_USER  # Send to self
        self.from_email = settings.DEFAULT_FROM_EMAIL
        
    def get_jobs_for_digest(self, days_back=1, min_score=70):
        """Get jobs for email digest"""
        since_date = timezone.now() - timedelta(days=days_back)
        
        # Get high-scoring jobs from the last few days
        top_jobs = JobScore.objects.filter(
            job__is_active=True,
            job__scraped_at__gte=since_date,
            total_score__gte=min_score
        ).select_related('job', 'job__company').order_by('-total_score')
        
        # Get jobs that meet minimum requirements if we don't have enough high scores
        meets_minimum = JobScore.objects.filter(
            job__is_active=True,
            job__scraped_at__gte=since_date,
            total_score__gte=40,
            total_score__lt=min_score,
            meets_minimum_requirements=True
        ).select_related('job', 'job__company').order_by('-total_score')
        
        return {
            'top_matches': list(top_jobs[:10]),
            'worth_applying': list(meets_minimum[:10])
        }
    
    def should_send_digest(self, jobs_data):
        """Check if we should send the digest based on job count and quality"""
        top_matches = jobs_data.get('top_matches', [])
        worth_applying = jobs_data.get('worth_applying', [])
        
        # Send if we have at least 3 jobs scoring 70+
        if len(top_matches) >= 3:
            return True
            
        # Or if we have at least 5 jobs meeting minimum requirements
        if len(top_matches) + len(worth_applying) >= 5:
            return True
            
        return False
    
    def create_email_content(self, jobs_data):
        """Create email subject and body"""
        top_matches = jobs_data.get('top_matches', [])
        worth_applying = jobs_data.get('worth_applying', [])
        
        total_jobs = len(top_matches) + len(worth_applying)
        highest_score = top_matches[0].total_score if top_matches else 0
        
        # Create subject
        if top_matches:
            subject = f"🎯 Daily Job Digest: {len(top_matches)} Top Matches (Best: {highest_score:.1f})"
        else:
            subject = f"📧 Daily Job Digest: {total_jobs} Jobs for Review"
        
        # Create email body
        context = {
            'top_matches': top_matches,
            'worth_applying': worth_applying,
            'total_jobs': total_jobs,
            'highest_score': highest_score,
            'date': timezone.now().strftime('%B %d, %Y'),
        }
        
        # HTML version
        html_body = self.create_html_body(context)
        
        # Plain text version
        text_body = self.create_text_body(context)
        
        return subject, html_body, text_body
    
    def create_html_body(self, context):
        """Create HTML email body"""
        html_template = """
        <html>
        <head>
            <style>
                body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
                .header { background: #2c3e50; color: white; padding: 20px; text-align: center; }
                .section { margin: 20px 0; }
                .job { border: 1px solid #ddd; margin: 15px 0; padding: 15px; border-radius: 5px; }
                .job-title { color: #2c3e50; font-size: 18px; font-weight: bold; }
                .company { color: #7f8c8d; font-size: 16px; }
                .score { background: #27ae60; color: white; padding: 5px 10px; border-radius: 15px; font-weight: bold; }
                .score.fair { background: #f39c12; }
                .skills { margin: 10px 0; }
                .skill { background: #ecf0f1; padding: 3px 8px; border-radius: 3px; margin-right: 5px; display: inline-block; font-size: 12px; }
                .skill.matched { background: #d4edda; color: #155724; }
                .apply-btn { background: #3498db; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; }
                .footer { background: #34495e; color: white; padding: 15px; text-align: center; font-size: 12px; }
            </style>
        </head>
        <body>
            <div class="header">
                <h1>🎯 Your Daily Job Matches</h1>
                <p>{{ date }}</p>
            </div>
            
            {% if top_matches %}
                <div class="section">
                    <h2>🌟 Top Matches (85+ Score)</h2>
                    {% for job_score in top_matches %}
                        <div class="job">
                            <div class="job-title">{{ job_score.job.title }}</div>
                            <div class="company">{{ job_score.job.company.name }}</div>
                            <div style="margin: 10px 0;">
                                <span class="score">{{ job_score.total_score|floatformat:1 }}</span>
                                <span style="margin-left: 10px;">📍 {{ job_score.job.location }}</span>
                                {% if job_score.job.salary_min %}
                                    <span style="margin-left: 10px;">💰 {{ job_score.job.salary_range_str }}</span>
                                {% endif %}
                            </div>
                            <div class="skills">
                                <strong>Your Matching Skills:</strong>
                                {% for skill in job_score.matching_skills|slice:":5" %}
                                    <span class="skill matched">{{ skill }}</span>
                                {% endfor %}
                            </div>
                            <p>{{ job_score.job.description|truncatewords:25 }}</p>
                            <a href="{{ job_score.job.source_url }}" class="apply-btn">Apply Now</a>
                        </div>
                    {% endfor %}
                </div>
            {% endif %}
            
            {% if worth_applying %}
                <div class="section">
                    <h2>📝 Worth Applying (70-84 Score)</h2>
                    {% for job_score in worth_applying %}
                        <div class="job">
                            <div class="job-title">{{ job_score.job.title }}</div>
                            <div class="company">{{ job_score.job.company.name }}</div>
                            <div style="margin: 10px 0;">
                                <span class="score fair">{{ job_score.total_score|floatformat:1 }}</span>
                                <span style="margin-left: 10px;">📍 {{ job_score.job.location }}</span>
                            </div>
                            <div class="skills">
                                {% for skill in job_score.matching_skills|slice:":4" %}
                                    <span class="skill matched">{{ skill }}</span>
                                {% endfor %}
                            </div>
                            <a href="{{ job_score.job.source_url }}" class="apply-btn">Apply Now</a>
                        </div>
                    {% endfor %}
                </div>
            {% endif %}
            
            <div class="footer">
                <p>This is your personalized job finder. Good luck with your applications! 🍀</p>
                <p>Generated automatically at 7 PM EST</p>
            </div>
        </body>
        </html>
        """
        
        from django.template import Template, Context
        template = Template(html_template)
        return template.render(Context(context))
    
    def create_text_body(self, context):
        """Create plain text email body"""
        text_lines = [
            "🎯 Your Daily Job Matches",
            f"Date: {context['date']}",
            "=" * 50,
            ""
        ]
        
        if context['top_matches']:
            text_lines.extend([
                "🌟 TOP MATCHES (85+ Score):",
                "-" * 30
            ])
            
            for job_score in context['top_matches']:
                job = job_score.job
                text_lines.extend([
                    f"• {job.title} at {job.company.name}",
                    f"  Score: {job_score.total_score:.1f} | Location: {job.location}",
                    f"  Skills: {', '.join(job_score.matching_skills[:5])}",
                    f"  Apply: {job.source_url}",
                    ""
                ])
        
        if context['worth_applying']:
            text_lines.extend([
                "📝 WORTH APPLYING (70-84 Score):",
                "-" * 35
            ])
            
            for job_score in context['worth_applying']:
                job = job_score.job
                text_lines.extend([
                    f"• {job.title} at {job.company.name}",
                    f"  Score: {job_score.total_score:.1f} | Location: {job.location}",
                    f"  Apply: {job.source_url}",
                    ""
                ])
        
        text_lines.extend([
            "=" * 50,
            "Good luck with your applications! 🍀",
            "Generated automatically at 7 PM EST"
        ])
        
        return "\n".join(text_lines)
    
    def send_digest(self):
        """Send the daily email digest"""
        try:
            # Get jobs for digest
            jobs_data = self.get_jobs_for_digest()
            
            # Check if we should send
            if not self.should_send_digest(jobs_data):
                logger.info("Not enough quality jobs for digest. Skipping email.")
                return False
            
            # Create email content
            subject, html_body, text_body = self.create_email_content(jobs_data)
            
            # Send email
            send_mail(
                subject=subject,
                message=text_body,
                from_email=self.from_email,
                recipient_list=[self.recipient_email],
                html_message=html_body,
                fail_silently=False
            )
            
            # Save digest record
            all_jobs = jobs_data['top_matches'] + jobs_data['worth_applying']
            job_objects = [js.job for js in all_jobs]
            
            digest = EmailDigest.objects.create(
                recipient_email=self.recipient_email,
                subject=subject,
                jobs_count=len(job_objects),
                top_score=all_jobs[0].total_score if all_jobs else 0,
                email_sent_successfully=True
            )
            
            digest.jobs_included.set(job_objects)
            
            logger.info(f"Successfully sent email digest with {len(job_objects)} jobs")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send email digest: {str(e)}")
            
            # Save failed digest record
            EmailDigest.objects.create(
                recipient_email=self.recipient_email,
                subject=f"Failed Digest - {timezone.now().strftime('%Y-%m-%d')}",
                jobs_count=0,
                email_sent_successfully=False
            )
            
            return False