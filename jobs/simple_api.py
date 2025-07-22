"""
Simple API views without DRF to avoid complexity
"""
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.core.paginator import Paginator
from django.db.models import Q
import json

from .models import Job, JobScore, Company, EmailDigest


@require_http_methods(["GET"])
def simple_dashboard_api(request):
    """Simple dashboard API without DRF"""
    try:
        # Get job statistics
        total_jobs = Job.objects.filter(is_active=True).count()
        recommended_jobs = JobScore.objects.filter(
            job__is_active=True,
            recommended_for_application=True
        ).count()
        
        meets_minimum = JobScore.objects.filter(
            job__is_active=True,
            meets_minimum_requirements=True
        ).count()
        
        # Latest scraping info
        latest_job = Job.objects.filter(is_active=True).order_by('-scraped_at').first()
        last_scrape_date = latest_job.scraped_at if latest_job else None
        
        # Email digest info
        latest_digest = EmailDigest.objects.order_by('-sent_at').first()
        last_email_date = latest_digest.sent_at if latest_digest else None
        
        # Top scoring jobs
        top_jobs_qs = Job.objects.filter(
            is_active=True,
            score__isnull=False
        ).select_related('company', 'score').order_by('-score__total_score')[:4]
        
        # Recent jobs
        recent_jobs_qs = Job.objects.filter(
            is_active=True
        ).select_related('company', 'score').order_by('-scraped_at')[:4]
        
        # Convert jobs to simple dicts
        def job_to_dict(job):
            return {
                'id': job.id,
                'title': job.title,
                'company': {
                    'id': job.company.id,
                    'name': job.company.name,
                    'location': job.company.location,
                    'company_type': job.company.company_type,
                },
                'location': job.location,
                'location_type': job.location_type,
                'salary_min': job.salary_min,
                'salary_max': job.salary_max,
                'experience_level': job.experience_level,
                'posted_date': job.posted_date.isoformat(),
                'required_skills': job.required_skills or [],
                'employment_type': job.employment_type,
                'is_entry_level_friendly': job.is_entry_level_friendly,
                'score': {
                    'total_score': job.score.total_score if job.score else 0,
                    'skills_score': job.score.skills_match_score if job.score else 0,
                    'recommended_for_application': job.score.recommended_for_application if job.score else False,
                } if hasattr(job, 'score') and job.score else None
            }
        
        data = {
            'total_jobs': total_jobs,
            'recommended_jobs': recommended_jobs,
            'meets_minimum': meets_minimum,
            'last_scrape_date': last_scrape_date.isoformat() if last_scrape_date else None,
            'last_email_date': last_email_date.isoformat() if last_email_date else None,
            'top_jobs': [job_to_dict(job) for job in top_jobs_qs],
            'recent_jobs': [job_to_dict(job) for job in recent_jobs_qs],
        }
        
        return JsonResponse(data)
    
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@require_http_methods(["GET"])
def simple_jobs_api(request):
    """Simple jobs list API"""
    try:
        jobs_qs = Job.objects.filter(is_active=True).select_related('company', 'score')
        
        # Simple search
        search = request.GET.get('search', '').strip()
        if search:
            jobs_qs = jobs_qs.filter(
                Q(title__icontains=search) |
                Q(company__name__icontains=search)
            )
        
        # Simple sorting
        sort_by = request.GET.get('sort', 'score')
        if sort_by == 'score':
            jobs_qs = jobs_qs.order_by('-score__total_score', '-posted_date')
        elif sort_by == 'date':
            jobs_qs = jobs_qs.order_by('-posted_date')
        else:
            jobs_qs = jobs_qs.order_by('-score__total_score', '-posted_date')
        
        # Pagination
        page = request.GET.get('page', 1)
        paginator = Paginator(jobs_qs, 20)
        jobs_page = paginator.get_page(page)
        
        # Convert to dict
        def job_to_dict(job):
            return {
                'id': job.id,
                'title': job.title,
                'company': {
                    'id': job.company.id,
                    'name': job.company.name,
                    'location': job.company.location,
                    'company_type': job.company.company_type,
                },
                'location': job.location,
                'location_type': job.location_type,
                'salary_min': job.salary_min,
                'salary_max': job.salary_max,
                'experience_level': job.experience_level,
                'posted_date': job.posted_date.isoformat(),
                'required_skills': job.required_skills or [],
                'employment_type': job.employment_type,
                'is_entry_level_friendly': job.is_entry_level_friendly,
                'score': {
                    'total_score': job.score.total_score if job.score else 0,
                    'skills_score': job.score.skills_match_score if job.score else 0,
                    'recommended_for_application': job.score.recommended_for_application if job.score else False,
                } if hasattr(job, 'score') and job.score else None
            }
        
        data = {
            'count': paginator.count,
            'results': [job_to_dict(job) for job in jobs_page]
        }
        
        return JsonResponse(data)
    
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@require_http_methods(["GET"])
def simple_job_detail_api(request, job_id):
    """Simple job detail API"""
    try:
        job = Job.objects.select_related('company', 'score').get(id=job_id, is_active=True)
        
        data = {
            'id': job.id,
            'title': job.title,
            'company': {
                'id': job.company.id,
                'name': job.company.name,
                'location': job.company.location,
                'website': job.company.website,
                'company_type': job.company.company_type,
            },
            'description': job.description,
            'location': job.location,
            'location_type': job.location_type,
            'source': job.source,
            'source_url': job.source_url,
            'salary_min': job.salary_min,
            'salary_max': job.salary_max,
            'experience_level': job.experience_level,
            'posted_date': job.posted_date.isoformat(),
            'scraped_at': job.scraped_at.isoformat(),
            'required_skills': job.required_skills or [],
            'employment_type': job.employment_type,
            'is_entry_level_friendly': job.is_entry_level_friendly,
            'score': {
                'total_score': job.score.total_score if job.score else 0,
                'skills_score': job.score.skills_match_score if job.score else 0,
                'experience_score': job.score.experience_match_score if job.score else 0,
                'location_score': job.score.location_preference_score if job.score else 0,
                'salary_score': job.score.salary_match_score if job.score else 0,
                'company_score': job.score.company_type_score if job.score else 0,
                'matching_skills': job.score.matching_skills if job.score else [],
                'missing_skills': job.score.missing_skills if job.score else [],
                'meets_minimum_requirements': job.score.meets_minimum_requirements if job.score else False,
                'recommended_for_application': job.score.recommended_for_application if job.score else False,
            } if hasattr(job, 'score') and job.score else None
        }
        
        return JsonResponse(data)
    
    except Job.DoesNotExist:
        return JsonResponse({'error': 'Job not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)