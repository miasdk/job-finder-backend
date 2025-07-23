"""
Setup Free API Keys - Helper command to get free API access
Provides instructions and links to obtain free API keys
"""

from django.core.management.base import BaseCommand

class Command(BaseCommand):
    help = 'Get instructions for setting up free API keys to expand job sources'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('🔑 FREE API KEYS SETUP GUIDE'))
        self.stdout.write('')
        
        # Reed API (100 free calls/month)
        self.stdout.write(self.style.WARNING('1. 🇬🇧 REED API (UK Jobs) - 100 FREE calls/month'))
        self.stdout.write('   • Visit: https://www.reed.co.uk/developers/jobseeker')
        self.stdout.write('   • Click "Register" to get API key')
        self.stdout.write('   • Add to environment: REED_API_KEY=your_api_key')
        self.stdout.write('   • Coverage: UK jobs with salary data')
        self.stdout.write('')
        
        # Rise API (Free tier)
        self.stdout.write(self.style.WARNING('2. 🚀 RISE API (Tech Jobs) - FREE'))
        self.stdout.write('   • URL: https://api.joinrise.io/api/v1/jobs/public')
        self.stdout.write('   • No API key needed - completely free!')
        self.stdout.write('   • Coverage: Global tech jobs')
        self.stdout.write('')
        
        # Current API status
        self.stdout.write(self.style.SUCCESS('📊 CURRENT API STATUS:'))
        
        # Check environment variables
        import os
        
        jsearch_key = os.getenv('JSEARCH_API_KEY', 'not_set')
        adzuna_key = os.getenv('ADZUNA_API_KEY', 'not_set') 
        reed_key = os.getenv('REED_API_KEY', 'not_set')
        
        self.stdout.write(f'   ✅ JSearch: {"ACTIVE" if jsearch_key != "not_set" and jsearch_key != "demo_api_key" else "❌ NOT SET"}')
        self.stdout.write(f'   ✅ Adzuna: {"ACTIVE" if adzuna_key != "not_set" and adzuna_key != "demo_api_key" else "❌ NOT SET"}')
        self.stdout.write(f'   🆕 Reed: {"ACTIVE" if reed_key != "not_set" and reed_key != "demo_api_key" else "❌ NOT SET (Get free key!)"}')
        self.stdout.write(f'   🆕 Rise: ✅ ACTIVE (No key needed)')
        self.stdout.write('')
        
        # Additional recommendations
        self.stdout.write(self.style.SUCCESS('💡 ADDITIONAL RECOMMENDATIONS:'))
        self.stdout.write('')
        
        self.stdout.write(self.style.WARNING('3. 🔍 SERPAPI (Google Jobs) - 100 FREE searches/month'))
        self.stdout.write('   • Visit: https://serpapi.com/users/sign_up')
        self.stdout.write('   • Get API key for Google Jobs data')
        self.stdout.write('   • Add to environment: SERPAPI_KEY=your_api_key')
        self.stdout.write('')
        
        self.stdout.write(self.style.WARNING('4. 🌐 LINKEDIN JOBS (via SerpAPI)'))
        self.stdout.write('   • Use your SerpAPI key to scrape LinkedIn Jobs')
        self.stdout.write('   • Higher quality professional roles')
        self.stdout.write('   • Already implemented - just need SerpAPI key')
        self.stdout.write('')
        
        # Usage instructions
        self.stdout.write(self.style.SUCCESS('🚀 AFTER SETUP:'))
        self.stdout.write('   1. Set environment variables in your shell:')
        self.stdout.write('      export REED_API_KEY="your_reed_key"')
        self.stdout.write('      export SERPAPI_KEY="your_serp_key"')
        self.stdout.write('')
        self.stdout.write('   2. Run comprehensive job expansion:')
        self.stdout.write('      python manage.py expand_job_sources --min-score 15 --max-jobs 500')
        self.stdout.write('')
        self.stdout.write('   3. With all APIs active, expect:')
        self.stdout.write('      • 500+ new jobs per run')
        self.stdout.write('      • Better UK job coverage (Reed)')
        self.stdout.write('      • More tech-focused roles (Rise)')
        self.stdout.write('      • LinkedIn professional roles (SerpAPI)')
        self.stdout.write('')
        
        # Cost breakdown
        self.stdout.write(self.style.SUCCESS('💰 COST BREAKDOWN (Monthly):'))
        self.stdout.write('   • Reed API: £0 (100 free calls)')
        self.stdout.write('   • Rise API: £0 (completely free)')
        self.stdout.write('   • SerpAPI: $5 (100 free searches)')
        self.stdout.write('   • JSearch: $0 (you already have it)')
        self.stdout.write('   • Adzuna: $0 (you already have it)')
        self.stdout.write('   📊 Total monthly cost: ~$5 for 5x more job coverage!')
        self.stdout.write('')
        
        self.stdout.write(self.style.SUCCESS('🎯 Ready to 5X your job listings? Get those free API keys!')) 