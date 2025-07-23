from rest_framework import generics, status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from django.db.models import Q
from django.shortcuts import get_object_or_404

from .models import Job, JobScore, EmailDigest, Company
from .serializers import (
    JobSerializer, JobListSerializer, CompanySerializer,
    EmailDigestSerializer, DashboardStatsSerializer
)
from .scoring import JobScorer


class JobPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100


class JobListAPIView(generics.ListAPIView):
    """API endpoint for job listings with filtering and search"""
    serializer_class = JobListSerializer
    pagination_class = JobPagination
    
    def get_queryset(self):
        queryset = Job.objects.filter(is_active=True).select_related('company', 'score')
        
        # Search functionality
        search_query = self.request.query_params.get('search', '')
        if search_query:
            queryset = queryset.filter(
                Q(title__icontains=search_query) |
                Q(description__icontains=search_query) |
                Q(company__name__icontains=search_query) |
                Q(required_skills__icontains=search_query)
            )
        
        # Filters
        location = self.request.query_params.get('location')
        if location:
            queryset = queryset.filter(location__icontains=location)
        
        experience_level = self.request.query_params.get('experience_level')
        if experience_level:
            queryset = queryset.filter(experience_level=experience_level)
        
        min_score = self.request.query_params.get('min_score')
        if min_score:
            try:
                min_score_val = float(min_score)
                queryset = queryset.filter(score__total_score__gte=min_score_val)
            except (ValueError, TypeError):
                pass
        
        location_type = self.request.query_params.get('location_type')
        if location_type:
            queryset = queryset.filter(location_type=location_type)
        
        # Sorting
        sort_by = self.request.query_params.get('sort', 'score')
        if sort_by == 'score':
            queryset = queryset.order_by('-score__total_score', '-posted_date')
        elif sort_by == 'date':
            queryset = queryset.order_by('-posted_date')
        elif sort_by == 'company':
            queryset = queryset.order_by('company__name', '-score__total_score')
        else:
            queryset = queryset.order_by('-score__total_score', '-posted_date')
        
        return queryset


class JobDetailAPIView(generics.RetrieveAPIView):
    """API endpoint for job detail"""
    serializer_class = JobSerializer
    
    def get_object(self):
        job_id = self.kwargs['pk']
        return get_object_or_404(
            Job.objects.select_related('company', 'score'),
            id=job_id,
            is_active=True
        )


@api_view(['GET'])
def dashboard_stats_api(request):
    """API endpoint for dashboard statistics"""
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
    top_jobs_qs = Job.objects.filter(
        is_active=True,
        score__isnull=False
    ).select_related('company', 'score').order_by('-score__total_score')[:10]
    
    # Recent jobs
    recent_jobs_qs = Job.objects.filter(
        is_active=True
    ).select_related('company', 'score').order_by('-scraped_at')[:10]
    
    # Company stats
    company_stats_qs = Company.objects.filter(
        jobs__is_active=True
    ).distinct().order_by('name')[:10]
    
    # Recent email digests
    email_digests_qs = EmailDigest.objects.order_by('-sent_at')[:5]
    
    # Serialize the data
    data = {
        'total_jobs': total_jobs,
        'recommended_jobs': recommended_jobs,
        'meets_minimum': meets_minimum,
        'top_jobs': JobListSerializer(top_jobs_qs, many=True).data,
        'recent_jobs': JobListSerializer(recent_jobs_qs, many=True).data,
        'company_stats': CompanySerializer(company_stats_qs, many=True).data,
        'email_digests': EmailDigestSerializer(email_digests_qs, many=True).data,
    }
    
    serializer = DashboardStatsSerializer(data)
    return Response(serializer.data)


@api_view(['POST'])
def score_job_api(request, job_id):
    """API endpoint to score/rescore a specific job"""
    job = get_object_or_404(Job, id=job_id)
    scorer = JobScorer()
    
    try:
        job_score = scorer.score_job(job)
        return Response({
            'success': True,
            'score': job_score.total_score,
            'recommended': job_score.recommended_for_application,
            'matching_skills': job_score.matching_skills,
            'missing_skills': job_score.missing_skills,
            'meets_minimum_requirements': job_score.meets_minimum_requirements,
        })
    except Exception as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
def companies_api(request):
    """API endpoint to get companies list for autocomplete"""
    companies = Company.objects.all().values('id', 'name').order_by('name')
    return Response(list(companies))


@api_view(['GET'])
def skills_api(request):
    """API endpoint to get all skills for autocomplete"""
    # For SQLite compatibility, use a simple approach
    skills_set = set()
    
    try:
        # Get all jobs and extract skills
        jobs = Job.objects.filter(is_active=True).values_list('required_skills', flat=True)
        for skills_list in jobs:
            if skills_list:
                for skill in skills_list:
                    skills_set.add(skill)
        
        skills = sorted(list(skills_set))
    except Exception:
        # Fallback: get skills from a predefined list
        skills = [
            'Python', 'Django', 'Django REST Framework', 'PostgreSQL', 'React',
            'Next.js', 'TypeScript', 'JavaScript', 'Node.js', 'Express',
            'HTML', 'CSS', 'TailwindCSS', 'AWS', 'Docker', 'Git', 'CI/CD',
            'Jest', 'OAuth', 'Pandas', 'NumPy', 'Flask', 'Celery', 'Redis',
            'Firebase', 'SQL', 'MongoDB', 'REST API', 'GraphQL', 'Linux',
            'Kubernetes'
        ]
    
    return Response(skills)


class CompanyListAPIView(generics.ListAPIView):
    """API endpoint for companies"""
    serializer_class = CompanySerializer
    queryset = Company.objects.all().order_by('name')