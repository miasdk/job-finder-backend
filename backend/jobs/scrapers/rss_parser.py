"""
Custom RSS parser that's compatible with Python 3.13
Replaces feedparser functionality for Indeed RSS feeds
"""

import xml.etree.ElementTree as ET
import requests
from datetime import datetime
import logging
from typing import List, Dict, Optional
from urllib.parse import quote_plus

logger = logging.getLogger('jobs')

class RSSParser:
    """Custom RSS parser compatible with Python 3.13"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
    
    def parse_rss_feed(self, url: str) -> List[Dict]:
        """Parse RSS feed from URL and return list of job entries"""
        try:
            logger.info(f"Fetching RSS feed: {url}")
            
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            
            # Parse XML
            root = ET.fromstring(response.content)
            
            # Find all items in the RSS feed
            items = []
            for item in root.findall('.//item'):
                try:
                    entry = self._parse_item(item)
                    if entry:
                        items.append(entry)
                except Exception as e:
                    logger.warning(f"Error parsing RSS item: {str(e)}")
                    continue
            
            logger.info(f"Successfully parsed {len(items)} items from RSS feed")
            return items
            
        except requests.RequestException as e:
            logger.error(f"Error fetching RSS feed {url}: {str(e)}")
            return []
        except ET.ParseError as e:
            logger.error(f"Error parsing XML from {url}: {str(e)}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error parsing RSS feed {url}: {str(e)}")
            return []
    
    def _parse_item(self, item: ET.Element) -> Optional[Dict]:
        """Parse individual RSS item into job data"""
        try:
            entry = {}
            
            # Basic fields
            title = item.find('title')
            entry['title'] = title.text if title is not None else ""
            
            link = item.find('link')
            entry['link'] = link.text if link is not None else ""
            
            description = item.find('description')
            entry['summary'] = description.text if description is not None else ""
            
            # Publication date
            pub_date = item.find('pubDate')
            if pub_date is not None:
                entry['published'] = pub_date.text
                entry['published_date'] = self._parse_date(pub_date.text)
            else:
                entry['published'] = None
                entry['published_date'] = None
            
            # GUID (unique identifier)
            guid = item.find('guid')
            entry['guid'] = guid.text if guid is not None else entry['link']
            
            return entry
            
        except Exception as e:
            logger.error(f"Error parsing RSS item: {str(e)}")
            return None
    
    def _parse_date(self, date_str: str) -> Optional[datetime]:
        """Parse RSS date string into datetime object"""
        if not date_str:
            return None
        
        # Common RSS date formats
        date_formats = [
            "%a, %d %b %Y %H:%M:%S %z",  # RFC 2822 format
            "%a, %d %b %Y %H:%M:%S GMT",
            "%a, %d %b %Y %H:%M:%S",
            "%Y-%m-%dT%H:%M:%S%z",  # ISO format
            "%Y-%m-%d %H:%M:%S",
        ]
        
        for fmt in date_formats:
            try:
                return datetime.strptime(date_str.strip(), fmt)
            except ValueError:
                continue
        
        logger.warning(f"Could not parse date: {date_str}")
        return None

class IndeedRSSManager:
    """Manager for Indeed RSS feeds with fallback scraping"""
    
    def __init__(self):
        self.rss_parser = RSSParser()
        self.base_url = "https://www.indeed.com/rss"
    
    def build_rss_url(self, query: str, location: str = "New York, NY") -> str:
        """Build Indeed RSS URL for given query and location"""
        encoded_query = quote_plus(query)
        encoded_location = quote_plus(location)
        
        # Indeed RSS parameters
        params = {
            'q': encoded_query,
            'l': encoded_location,
            'sort': 'date',  # Sort by date
            'fromage': '7',  # Jobs from last 7 days
            'limit': '50',   # Max results
        }
        
        param_string = '&'.join([f"{k}={v}" for k, v in params.items()])
        return f"{self.base_url}?{param_string}"
    
    def get_jobs_from_rss(self, search_terms: List[str], location: str = "New York, NY") -> List[Dict]:
        """Get jobs from Indeed RSS feeds for multiple search terms"""
        all_jobs = []
        
        for search_term in search_terms:
            try:
                logger.info(f"Fetching RSS feed for: {search_term} in {location}")
                
                rss_url = self.build_rss_url(search_term, location)
                jobs = self.rss_parser.parse_rss_feed(rss_url)
                
                # Add metadata
                for job in jobs:
                    job['search_term'] = search_term
                    job['source'] = 'indeed'
                
                all_jobs.extend(jobs)
                
            except Exception as e:
                logger.error(f"Error processing search term '{search_term}': {str(e)}")
                continue
        
        # Remove duplicates based on URL
        unique_jobs = {}
        for job in all_jobs:
            url = job.get('link', '')
            if url and url not in unique_jobs:
                unique_jobs[url] = job
        
        logger.info(f"Found {len(unique_jobs)} unique jobs from Indeed RSS")
        return list(unique_jobs.values())