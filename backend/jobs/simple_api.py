"""
Simple API views without DRF to avoid complexity
"""
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.core.paginator import Paginator
from django.db.models import Q
import json
import logging
from django.db.models import Count, Avg
from collections import Counter
import statistics
from datetime import timedelta
from django.utils import timezone

from .models import Job, JobScore, Company, EmailDigest, UserPreferences
from django.core.management import call_command
import io
import sys

logger = logging.getLogger(__name__)


@require_http_methods(["GET"])
def simple_dashboard_api(request):
    """Enhanced dashboard API with AI intelligence insights"""
    try:
        # Get user preferences for personalization
        user_preferences = UserPreferences.get_active_preferences()
        
        # Basic job statistics
        total_jobs = Job.objects.filter(is_active=True).count()
        recommended_jobs = JobScore.objects.filter(
            job__is_active=True,
            recommended_for_application=True
        ).count()
        
        meets_minimum = JobScore.objects.filter(
            job__is_active=True,
            meets_minimum_requirements=True
        ).count()
        
        # AI-POWERED INSIGHTS
        
        # 1. Skills Intelligence - What skills are in demand?
        all_job_skills = []
        jobs_with_skills = Job.objects.filter(is_active=True, required_skills__isnull=False).exclude(required_skills__exact=[])
        for job in jobs_with_skills:
            if job.required_skills:
                all_job_skills.extend(job.required_skills)
        
        skill_counts = Counter(all_job_skills)
        top_market_skills = [{'skill': skill, 'count': count} for skill, count in skill_counts.most_common(8)]
        
        # 2. Your Skills vs Market Demand
        user_skills = user_preferences.skills if user_preferences.skills else []
        user_skill_demand = []
        for skill in user_skills[:6]:  # Top 6 user skills
            count = skill_counts.get(skill, 0)
            user_skill_demand.append({'skill': skill, 'market_demand': count})
        
        # 3. Salary Intelligence
        jobs_with_salary = Job.objects.filter(is_active=True, salary_min__isnull=False, salary_min__gt=0)
        if jobs_with_salary.exists():
            salaries = [job.salary_min for job in jobs_with_salary]
            avg_salary = int(statistics.mean(salaries)) if salaries else 0
            median_salary = int(statistics.median(salaries)) if salaries else 0
            
            # Your target vs market
            market_comparison = {
                'your_min': user_preferences.min_salary,
                'your_max': user_preferences.max_salary,
                'market_avg': avg_salary,
                'market_median': median_salary,
                'above_market': user_preferences.min_salary > avg_salary
            }
        else:
            market_comparison = None
        
        # 4. Location Intelligence  
        location_stats = []
        jobs_by_location = Job.objects.filter(is_active=True).values('location').annotate(
            count=Count('id'),
            avg_score=Avg('score__total_score')
        ).order_by('-count')[:6]
        
        for loc_data in jobs_by_location:
            location_stats.append({
                'location': loc_data['location'],
                'job_count': loc_data['count'],
                'avg_score': round(loc_data['avg_score'] or 0, 1),
                'is_preferred': loc_data['location'] in user_preferences.preferred_locations
            })
        
        # 5. AI Recommendations Engine Status
        recent_scores = JobScore.objects.filter(
            job__is_active=True,
            updated_at__gte=timezone.now() - timedelta(hours=24)
        )
        
        ai_engine_stats = {
            'jobs_scored_today': recent_scores.count(),
            'avg_match_score': round(recent_scores.aggregate(Avg('total_score'))['total_score__avg'] or 0, 1),
            'high_matches': recent_scores.filter(total_score__gte=80).count(),
            'search_terms_used': user_preferences.job_titles[:3] if user_preferences.job_titles else ['Python Developer'],
            'active_scrapers': ['JSearch API', 'Adzuna', 'RemoteOK', 'Indeed', 'Wellfound']
        }
        
        # 6. Smart Job Alerts
        trending_companies = Job.objects.filter(
            is_active=True,
            score__total_score__gte=70
        ).values('company__name').annotate(
            count=Count('id'),
            avg_score=Avg('score__total_score')
        ).order_by('-avg_score')[:4]
        
        smart_alerts = []
        for company in trending_companies:
            smart_alerts.append({
                'company': company['company__name'],
                'high_match_jobs': company['count'],
                'avg_match': round(company['avg_score'], 1)
            })
        
        # Latest scraping info
        latest_job = Job.objects.filter(is_active=True).order_by('-scraped_at').first()
        last_scrape_date = latest_job.scraped_at if latest_job else None
        
        # Email digest info
        latest_digest = EmailDigest.objects.order_by('-sent_at').first()
        last_email_date = latest_digest.sent_at if latest_digest else None
        
        # Top scoring jobs (more intelligent selection)
        top_jobs_qs = Job.objects.filter(
            is_active=True,
            score__isnull=False,
            score__total_score__gte=60  # Only show decent matches
        ).select_related('company', 'score').order_by('-score__total_score')[:4]
        
        # Recent jobs with good scores
        recent_jobs_qs = Job.objects.filter(
            is_active=True,
            score__isnull=False
        ).select_related('company', 'score').order_by('-scraped_at')[:4]
        
        # Convert jobs to enhanced dicts
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
                'source': job.source,
                'source_url': job.source_url,
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
                    'matching_skills': job.score.matching_skills if job.score else [],
                    'missing_skills': job.score.missing_skills if job.score else [],
                    'recommended_for_application': job.score.recommended_for_application if job.score else False,
                } if hasattr(job, 'score') and job.score else None
            }
        
        data = {
            # Basic stats
            'total_jobs': total_jobs,
            'recommended_jobs': recommended_jobs,
            'meets_minimum': meets_minimum,
            'last_scrape_date': last_scrape_date.isoformat() if last_scrape_date else None,
            'last_email_date': last_email_date.isoformat() if last_email_date else None,
            
            # AI Intelligence Insights
            'skills_intelligence': {
                'top_market_skills': top_market_skills,
                'your_skills_demand': user_skill_demand,
                'recommendation': 'Focus on high-demand skills' if top_market_skills else 'Building skill database...'
            },
            'salary_intelligence': market_comparison,
            'location_intelligence': location_stats,
            'ai_engine_status': ai_engine_stats,
            'smart_company_alerts': smart_alerts,
            
            # Job lists (enhanced)
            'top_jobs': [job_to_dict(job) for job in top_jobs_qs],
            'recent_jobs': [job_to_dict(job) for job in recent_jobs_qs],
        }
        
        return JsonResponse(data)
    
    except Exception as e:
        logger.error(f"Dashboard API error: {e}")
        return JsonResponse({'error': str(e)}, status=500)


@require_http_methods(["GET"])
def simple_jobs_api(request):
    """Simple jobs list API"""
    try:
        jobs_qs = Job.objects.filter(is_active=True).select_related('company', 'score')
        
        # Filter by AI recommendation status
        filter_type = request.GET.get('filter', '')
        if filter_type == 'recommended':
            jobs_qs = jobs_qs.filter(score__recommended_for_application=True)
        elif filter_type == 'meets_requirements':
            jobs_qs = jobs_qs.filter(score__meets_minimum_requirements=True)
        
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
                'source': job.source,
                'source_url': job.source_url,
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
            try:
                from datetime import time
                time_str = str(data['email_time']).strip()
                if ':' in time_str:
                    hour, minute = map(int, time_str.split(':'))
                    prefs.email_time = time(hour, minute)
                else:
                    logger.warning(f"Invalid email_time format: {time_str}")
            except (ValueError, TypeError) as e:
                logger.warning(f"Failed to parse email_time '{data.get('email_time')}': {e}")
        if 'auto_scrape_enabled' in data:
            prefs.auto_scrape_enabled = data['auto_scrape_enabled']
        if 'scrape_frequency_hours' in data:
            prefs.scrape_frequency_hours = data['scrape_frequency_hours']
        if 'min_job_score_threshold' in data:
            prefs.min_job_score_threshold = data['min_job_score_threshold']
        
        prefs.save()
        
        # Light immediate rescoring - just top 20 jobs for instant feedback
        try:
            from .scoring import JobScorer
            
            # Only rescore top 20 recent jobs for immediate feedback
            scorer = JobScorer(prefs)
            jobs_to_rescore = Job.objects.filter(is_active=True).order_by('-posted_date')[:20]
            
            rescored_count = 0
            for job in jobs_to_rescore:
                try:
                    job_score = scorer.score_job(job)
                    rescored_count += 1
                except Exception as scoring_error:
                    logger.warning(f"Failed to score job {job.id}: {scoring_error}")
                    continue
            
            logger.info(f"Immediately rescored {rescored_count} recent jobs with updated preferences")
            
        except ImportError as e:
            logger.warning(f"Could not import JobScorer, skipping immediate rescoring: {e}")
        except Exception as e:
            logger.warning(f"Immediate rescoring failed: {e}")
        
        # Return updated preferences
        return JsonResponse({
            'success': True,
            'message': 'Preferences updated and jobs rescored successfully',
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


@csrf_exempt
@require_http_methods(["POST"])
def refresh_production_jobs(request):
    """API endpoint to refresh job listings with proper source URLs"""
    try:
        # Capture command output
        output = io.StringIO()
        call_command('api_refresh_jobs', stdout=output)
        result = json.loads(output.getvalue())
        
        return JsonResponse(result)
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@require_http_methods(["GET"])
def recommended_jobs_api(request):
    """API endpoint for AI recommended jobs only"""
    try:
        jobs_qs = Job.objects.filter(
            is_active=True,
            score__recommended_for_application=True
        ).select_related('company', 'score').order_by('-score__total_score', '-posted_date')
        
        # Simple search
        search = request.GET.get('search', '').strip()
        if search:
            jobs_qs = jobs_qs.filter(
                Q(title__icontains=search) |
                Q(company__name__icontains=search)
            )
        
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
                'source': job.source,
                'source_url': job.source_url,
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
                    'matching_skills': job.score.matching_skills if job.score else [],
                    'missing_skills': job.score.missing_skills if job.score else [],
                    'recommended_for_application': job.score.recommended_for_application if job.score else False,
                } if hasattr(job, 'score') and job.score else None
            }
        
        data = {
            'count': paginator.count,
            'results': [job_to_dict(job) for job in jobs_page],
            'filter_type': 'AI Recommended Jobs',
            'description': 'Jobs the AI strongly recommends for you based on your profile'
        }
        
        return JsonResponse(data)
    
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@require_http_methods(["GET"])
def meets_requirements_jobs_api(request):
    """API endpoint for jobs that meet minimum requirements"""
    try:
        jobs_qs = Job.objects.filter(
            is_active=True,
            score__meets_minimum_requirements=True
        ).select_related('company', 'score').order_by('-score__total_score', '-posted_date')
        
        # Simple search
        search = request.GET.get('search', '').strip()
        if search:
            jobs_qs = jobs_qs.filter(
                Q(title__icontains=search) |
                Q(company__name__icontains=search)
            )
        
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
                'source': job.source,
                'source_url': job.source_url,
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
                    'matching_skills': job.score.matching_skills if job.score else [],
                    'missing_skills': job.score.missing_skills if job.score else [],
                    'recommended_for_application': job.score.recommended_for_application if job.score else False,
                } if hasattr(job, 'score') and job.score else None
            }
        
        data = {
            'count': paginator.count,
            'results': [job_to_dict(job) for job in jobs_page],
            'filter_type': 'Meets Requirements',
            'description': 'Jobs where you meet the basic requirements and have a good chance'
        }
        
        return JsonResponse(data)
    
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)