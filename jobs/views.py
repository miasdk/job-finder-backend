from django.shortcuts import render, get_object_or_404
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import JsonResponse
from .models import Job, JobScore, EmailDigest, Company
from .scoring import JobScorer

def job_list(request):
    """Display list of jobs with filtering and sorting"""
    jobs = Job.objects.filter(is_active=True).select_related('company', 'score')
    
    # Filtering
    search_query = request.GET.get('q', '')
    location_filter = request.GET.get('location', '')
    experience_filter = request.GET.get('experience', '')
    min_score = request.GET.get('min_score', '')
    
    if search_query:
        jobs = jobs.filter(
            Q(title__icontains=search_query) |
            Q(description__icontains=search_query) |
            Q(company__name__icontains=search_query)
        )
    
    if location_filter:
        jobs = jobs.filter(location_type=location_filter)
    
    if experience_filter:
        jobs = jobs.filter(experience_level=experience_filter)
    
    if min_score:
        try:
            min_score_val = float(min_score)
            jobs = jobs.filter(score__total_score__gte=min_score_val)
        except ValueError:
            pass
    
    # Sorting
    sort_by = request.GET.get('sort', 'score')
    if sort_by == 'score':
        jobs = jobs.order_by('-score__total_score', '-posted_date')
    elif sort_by == 'date':
        jobs = jobs.order_by('-posted_date')
    elif sort_by == 'company':
        jobs = jobs.order_by('company__name', '-score__total_score')
    
    # Pagination
    paginator = Paginator(jobs, 20)
    page_number = request.GET.get('page')
    jobs_page = paginator.get_page(page_number)
    
    context = {
        'jobs': jobs_page,
        'search_query': search_query,
        'location_filter': location_filter,
        'experience_filter': experience_filter,
        'min_score': min_score,
        'sort_by': sort_by,
        'location_choices': Job.LOCATION_TYPES,
        'experience_choices': Job.EXPERIENCE_LEVELS,
    }
    
    return render(request, 'jobs/job_list.html', context)

def job_detail(request, job_id):
    """Display detailed view of a specific job"""
    job = get_object_or_404(Job.objects.select_related('company', 'score'), id=job_id)
    
    # Get related jobs from same company
    related_jobs = Job.objects.filter(
        company=job.company,
        is_active=True
    ).exclude(id=job.id).select_related('score')[:5]
    
    context = {
        'job': job,
        'related_jobs': related_jobs,
    }
    
    return render(request, 'jobs/job_detail.html', context)

def dashboard(request):
    """Display dashboard with job statistics"""
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
    
    # Top scoring jobs
    top_jobs = JobScore.objects.filter(
        job__is_active=True
    ).select_related('job', 'job__company').order_by('-total_score')[:10]
    
    # Recent jobs
    recent_jobs = Job.objects.filter(
        is_active=True
    ).select_related('company', 'score').order_by('-scraped_at')[:10]
    
    # Company breakdown
    company_stats = Company.objects.filter(
        jobs__is_active=True
    ).distinct().order_by('name')[:10]
    
    # Recent email digests
    email_digests = EmailDigest.objects.order_by('-sent_at')[:5]
    
    context = {
        'total_jobs': total_jobs,
        'recommended_jobs': recommended_jobs,
        'meets_minimum': meets_minimum,
        'top_jobs': top_jobs,
        'recent_jobs': recent_jobs,
        'company_stats': company_stats,
        'email_digests': email_digests,
    }
    
    return render(request, 'jobs/dashboard.html', context)

def score_job_ajax(request, job_id):
    """AJAX endpoint to score/rescore a specific job"""
    if request.method == 'POST':
        job = get_object_or_404(Job, id=job_id)
        scorer = JobScorer()
        
        try:
            job_score = scorer.score_job(job)
            return JsonResponse({
                'success': True,
                'score': job_score.total_score,
                'recommended': job_score.recommended_for_application,
                'matching_skills': job_score.matching_skills
            })
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            })
    
    return JsonResponse({'success': False, 'error': 'Invalid request method'})
