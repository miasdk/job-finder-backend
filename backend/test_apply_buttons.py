#!/usr/bin/env python3
"""
Test script to verify job listings have working apply buttons
"""
import requests
import json

def test_production_api():
    print("🔍 Testing production job listings API...")
    
    try:
        # Test the production API
        response = requests.get("https://job-finder-backend-5l5q.onrender.com/api/jobs/", timeout=30)
        response.raise_for_status()
        
        data = response.json()
        jobs = data.get('results', [])
        
        print(f"📊 Found {data.get('count', 0)} total jobs")
        print(f"🔗 Showing first {len(jobs)} jobs:\n")
        
        working_apply_buttons = 0
        
        for i, job in enumerate(jobs[:10], 1):
            title = job.get('title', 'Unknown Title')
            company = job.get('company', {}).get('name', 'Unknown Company')
            source = job.get('source', 'No source')
            source_url = job.get('source_url', 'No URL')
            
            # Check if apply button would work
            has_valid_url = source_url and source_url != 'No URL' and 'example.com' not in source_url
            status = "✅ Working apply button" if has_valid_url else "❌ Broken apply button"
            
            if has_valid_url:
                working_apply_buttons += 1
            
            print(f"{i}. {title}")
            print(f"   Company: {company}")
            print(f"   Source: {source}")
            print(f"   URL: {source_url}")
            print(f"   Status: {status}")
            print()
        
        print(f"📈 Summary: {working_apply_buttons}/{len(jobs[:10])} jobs have working apply buttons")
        
        if working_apply_buttons == 0:
            print("\n⚠️  No working apply buttons found!")
            print("💡 The deployment may not have updated yet, or the production database needs refresh.")
            print("🔧 You can run: python manage.py refresh_production_jobs --clear-existing")
        else:
            print(f"\n🎉 Success! {working_apply_buttons} jobs have working apply buttons!")
            
    except requests.RequestException as e:
        print(f"❌ Error accessing production API: {e}")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")

if __name__ == "__main__":
    test_production_api()