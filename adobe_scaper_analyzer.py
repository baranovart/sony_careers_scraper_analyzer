import csv
import os
import re
import time
import random
from typing import List, Dict

import requests
from bs4 import BeautifulSoup
from nltk.corpus import stopwords
from nltk.stem import PorterStemmer
import nltk

nltk.download('stopwords')

# List of common user agents
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36 Edg/91.0.864.59',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
]

def get_random_user_agent() -> str:
    """Returns a random user agent from the list of common user agents."""
    return random.choice(USER_AGENTS)

def get_working_dir():
    """Returns the absolute path of the script's working directory."""
    return os.path.abspath(os.path.dirname(__file__))

def scrape_adobe_careers(page_num: int, all_jobs: List[Dict]) -> None:
    """
    Scrapes job postings from Adobe's career site with improved selector handling.
    
    Args:
        page_num: Page number to scrape
        all_jobs: List to store found jobs
    """
    base_url = f"https://careers.adobe.com/us/en/search-results?from={page_num}&s=1"
    headers = {
        'User-Agent': get_random_user_agent(),
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate, br',
        'DNT': '1',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'none',
        'Sec-Fetch-User': '?1',
        'Cache-Control': 'max-age=0'
    }

    try:
        # Add a small random delay to avoid rate limiting
        time.sleep(random.uniform(1, 3))
        
        response = requests.get(base_url, headers=headers)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, "html.parser")

        # Rest of the scraping logic remains the same...
        job_postings = soup.select("table.table-hover tbody tr") or \
                      soup.select("[data-ph-at-id^='job-']") or \
                      soup.select(".job-search-result") or \
                      soup.select("[data-ph-at-data-row]")

        if not job_postings:
            print(f"Warning: No job postings found on page {page_num}. Check the HTML structure.")
            return

        for job_posting in job_postings:
            # Try multiple possible selectors for each field
            location = None
            location_selectors = [
                ("td[data-ph-at-job-location-text]", "text"),
                (".job-location", "text"),
                ("[data-ph-at-job-location]", "text"),
                ("[data-ph-job-location]", "attr:data-ph-job-location")
            ]
            
            for selector, extract_type in location_selectors:
                location_element = job_posting.select_one(selector)
                if location_element:
                    location = location_element.get_text(strip=True) if extract_type == "text" \
                              else location_element.get(extract_type.split(':')[1])
                    break

            if not location:
                print("Warning: Location not found in job posting. Skipping...")
                continue

            if "United States" in location or "US" in location:
                # Try multiple possible selectors for job title
                role = None
                role_url = None
                title_selectors = [
                    ("a[data-ph-at-job-title-text]", "text"),
                    (".job-title a", "text"),
                    ("[data-ph-at-job-title]", "text")
                ]
                
                for selector, extract_type in title_selectors:
                    title_element = job_posting.select_one(selector)
                    if title_element:
                        role = title_element.get_text(strip=True)
                        role_url = "https://careers.adobe.com" + title_element.get('href', '')
                        break

                if not role or not role_url:
                    print("Warning: Role or URL not found in job posting. Skipping...")
                    continue

                # Try multiple possible selectors for req ID
                req_id = None
                req_id_selectors = [
                    ("[data-ph-id]", "attr:data-ph-id"),
                    ("[data-ph-at-job-id]", "text"),
                    (".job-id", "text")
                ]
                
                for selector, extract_type in req_id_selectors:
                    req_id_element = job_posting.select_one(selector)
                    if req_id_element:
                        req_id = req_id_element.get(extract_type.split(':')[1]) if 'attr:' in extract_type \
                                else req_id_element.get_text(strip=True)
                        req_id = req_id.split('-')[-1] if '-' in req_id else req_id
                        break

                if not req_id:
                    print("Warning: Req ID not found in job posting. Skipping...")
                    continue

                print(f"Role: {role}")
                print(f"URL: {role_url}")
                print(f"Req ID: {req_id}")
                print(f"Location: {location}")
                print("-" * 20)

                all_jobs.append({
                    "role": role,
                    "role_url": role_url,
                    "req_id": req_id,
                    "location": location
                })

    except requests.exceptions.RequestException as e:
        print(f"Error fetching URL: {e}")
        print(f"Failed URL: {base_url}")