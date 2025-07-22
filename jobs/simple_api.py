"""
Simple API views without DRF to avoid complexity
"""
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.core.paginator import Paginator
from django.db.models import Q
import json

from .models import Job, JobScore, Company, EmailDigest, UserPreferences


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


@require_http_methods(["GET"])
def get_user_preferences(request):
    """Get user preferences"""
    try:
        # Ensure preferences exist, create defaults if needed
        prefs = UserPreferences.get_active_preferences()
        
        data = {
            'id': prefs.id,
            'name': prefs.name,
            'email': prefs.email,
            'skills': prefs.skills,
            'experience_levels': prefs.experience_levels,
            'min_experience_years': prefs.min_experience_years,
            'max_experience_years': prefs.max_experience_years,
            'preferred_locations': prefs.preferred_locations,
            'location_types': prefs.location_types,
            'min_salary': prefs.min_salary,
            'max_salary': prefs.max_salary,
            'currency': prefs.currency,
            'job_titles': prefs.job_titles,
            'preferred_companies': prefs.preferred_companies,
            'skills_weight': prefs.skills_weight,
            'experience_weight': prefs.experience_weight,
            'location_weight': prefs.location_weight,
            'salary_weight': prefs.salary_weight,
            'company_weight': prefs.company_weight,
            'email_enabled': prefs.email_enabled,
            'email_frequency': prefs.email_frequency,
            'email_time': prefs.email_time.strftime('%H:%M'),
            'auto_scrape_enabled': prefs.auto_scrape_enabled,
            'scrape_frequency_hours': prefs.scrape_frequency_hours,
            'min_job_score_threshold': prefs.min_job_score_threshold,
            'updated_at': prefs.updated_at.isoformat()
        }
        
        return JsonResponse(data)
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["POST", "PUT"])
def update_user_preferences(request):
    """Update user preferences"""
    try:
        data = json.loads(request.body)
        prefs = UserPreferences.get_active_preferences()
        
        # Update fields if provided
        if 'name' in data:
            prefs.name = data['name']
        if 'email' in data:
            prefs.email = data['email']
        if 'skills' in data:
            prefs.skills = data['skills']
        if 'experience_levels' in data:
            prefs.experience_levels = data['experience_levels']
        if 'min_experience_years' in data:
            prefs.min_experience_years = data['min_experience_years']
        if 'max_experience_years' in data:
            prefs.max_experience_years = data['max_experience_years']
        if 'preferred_locations' in data:
            prefs.preferred_locations = data['preferred_locations']
        if 'location_types' in data:
            prefs.location_types = data['location_types']
        if 'min_salary' in data:
            prefs.min_salary = data['min_salary']
        if 'max_salary' in data:
            prefs.max_salary = data['max_salary']
        if 'currency' in data:
            prefs.currency = data['currency']
        if 'job_titles' in data:
            prefs.job_titles = data['job_titles']
        if 'preferred_companies' in data:
            prefs.preferred_companies = data['preferred_companies']
        if 'skills_weight' in data:
            prefs.skills_weight = data['skills_weight']
        if 'experience_weight' in data:
            prefs.experience_weight = data['experience_weight']
        if 'location_weight' in data:
            prefs.location_weight = data['location_weight']
        if 'salary_weight' in data:
            prefs.salary_weight = data['salary_weight']
        if 'company_weight' in data:
            prefs.company_weight = data['company_weight']
        if 'email_enabled' in data:
            prefs.email_enabled = data['email_enabled']
        if 'email_frequency' in data:
            prefs.email_frequency = data['email_frequency']
        if 'email_time' in data:
            from datetime import time
            hour, minute = map(int, data['email_time'].split(':'))
            prefs.email_time = time(hour, minute)
        if 'auto_scrape_enabled' in data:
            prefs.auto_scrape_enabled = data['auto_scrape_enabled']
        if 'scrape_frequency_hours' in data:
            prefs.scrape_frequency_hours = data['scrape_frequency_hours']
        if 'min_job_score_threshold' in data:
            prefs.min_job_score_threshold = data['min_job_score_threshold']
        
        prefs.save()
        
        # Return updated preferences
        return JsonResponse({
            'success': True,
            'message': 'Preferences updated successfully',
            'preferences': {
                'id': prefs.id,
                'name': prefs.name,
                'email': prefs.email,
                'skills': prefs.skills,
                'experience_levels': prefs.experience_levels,
                'min_experience_years': prefs.min_experience_years,
                'max_experience_years': prefs.max_experience_years,
                'preferred_locations': prefs.preferred_locations,
                'location_types': prefs.location_types,
                'min_salary': prefs.min_salary,
                'max_salary': prefs.max_salary,
                'currency': prefs.currency,
                'job_titles': prefs.job_titles,
                'preferred_companies': prefs.preferred_companies,
                'skills_weight': prefs.skills_weight,
                'experience_weight': prefs.experience_weight,
                'location_weight': prefs.location_weight,
                'salary_weight': prefs.salary_weight,
                'company_weight': prefs.company_weight,
                'email_enabled': prefs.email_enabled,
                'email_frequency': prefs.email_frequency,
                'email_time': prefs.email_time.strftime('%H:%M'),
                'auto_scrape_enabled': prefs.auto_scrape_enabled,
                'scrape_frequency_hours': prefs.scrape_frequency_hours,
                'min_job_score_threshold': prefs.min_job_score_threshold,
                'updated_at': prefs.updated_at.isoformat()
            }
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)