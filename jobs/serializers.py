from rest_framework import serializers
from .models import Job, Company, JobScore, EmailDigest


class CompanySerializer(serializers.ModelSerializer):
    class Meta:
        model = Company
        fields = ['id', 'name', 'website', 'location', 'company_type', 'created_at']


class JobScoreSerializer(serializers.ModelSerializer):
    class Meta:
        model = JobScore
        fields = [
            'id', 'job', 'skills_score', 'experience_score', 'location_score',
            'salary_score', 'company_score', 'total_score', 'matching_skills',
            'missing_skills', 'meets_minimum_requirements', 'recommended_for_application',
            'scored_at'
        ]


class JobSerializer(serializers.ModelSerializer):
    company = CompanySerializer(read_only=True)
    score = JobScoreSerializer(read_only=True)
    
    class Meta:
        model = Job
        fields = [
            'id', 'title', 'company', 'description', 'location', 'location_type',
            'source', 'source_url', 'required_skills', 'salary_min', 'salary_max',
            'experience_level', 'posted_date', 'scraped_at', 'is_entry_level_friendly',
            'employment_type', 'is_active', 'score'
        ]


class JobListSerializer(serializers.ModelSerializer):
    """Lighter serializer for job listings"""
    company = CompanySerializer(read_only=True)
    score = JobScoreSerializer(read_only=True)
    
    class Meta:
        model = Job
        fields = [
            'id', 'title', 'company', 'location', 'location_type',
            'source', 'required_skills', 'salary_min', 'salary_max',
            'experience_level', 'posted_date', 'is_entry_level_friendly',
            'employment_type', 'score'
        ]


class EmailDigestSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmailDigest
        fields = [
            'id', 'sent_at', 'job_count', 'high_score_count', 'recommended_count',
            'email_subject', 'was_sent_successfully'
        ]


class DashboardStatsSerializer(serializers.Serializer):
    """Serializer for dashboard statistics"""
    total_jobs = serializers.IntegerField()
    recommended_jobs = serializers.IntegerField()
    meets_minimum = serializers.IntegerField()
    top_jobs = JobListSerializer(many=True)
    recent_jobs = JobListSerializer(many=True)
    company_stats = CompanySerializer(many=True)
    email_digests = EmailDigestSerializer(many=True)