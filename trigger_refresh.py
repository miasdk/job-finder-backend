#!/usr/bin/env python3
"""
Script to trigger production job refresh via API
"""
import requests
import time

def trigger_refresh():
    print("🔄 Triggering production job refresh...")
    
    try:
        # Wait a bit for deployment to complete
        print("⏳ Waiting 30 seconds for deployment to complete...")
        time.sleep(30)
        
        # Call the refresh API
        response = requests.post(
            "https://job-finder-backend-5l5q.onrender.com/api/refresh-jobs/",
            timeout=120  # Increase timeout for scraping
        )
        
        if response.status_code == 200:
            result = response.json()
            if result.get('success'):
                print("✅ Job refresh successful!")
                print(f"   📊 Deleted old jobs: {result.get('deleted_old_jobs', 0)}")
                print(f"   ➕ Added new jobs: {result.get('added_new_jobs', 0)}")
                print(f"   🎯 Total jobs now: {result.get('total_jobs', 0)}")
            else:
                print(f"❌ Job refresh failed: {result.get('error', 'Unknown error')}")
        else:
            print(f"❌ API call failed with status {response.status_code}")
            print(f"   Response: {response.text}")
            
    except requests.RequestException as e:
        print(f"❌ Error calling refresh API: {e}")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
    
    # Test the results
    print("\n🔍 Testing apply buttons after refresh...")
    time.sleep(5)  # Wait for changes to propagate
    
    try:
        response = requests.get("https://job-finder-backend-5l5q.onrender.com/api/jobs/", timeout=30)
        response.raise_for_status()
        
        data = response.json()
        jobs = data.get('results', [])
        working_buttons = 0
        
        for job in jobs[:5]:  # Check first 5 jobs
            source_url = job.get('source_url', '')
            if source_url and 'example.com' not in source_url and source_url != 'No URL':
                working_buttons += 1
        
        print(f"   📈 {working_buttons}/{min(len(jobs), 5)} jobs have working apply buttons")
        
        if working_buttons > 0:
            print("🎉 Success! Apply buttons should now work on the frontend!")
        else:
            print("⚠️  Still no working apply buttons. May need manual intervention.")
            
    except Exception as e:
        print(f"❌ Error testing results: {e}")

if __name__ == "__main__":
    trigger_refresh()