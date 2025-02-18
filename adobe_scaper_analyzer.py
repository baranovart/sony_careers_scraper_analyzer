import csv
import asyncio
import os
import re
from typing import List, Dict
from datetime import datetime

from pyppeteer import launch
from bs4 import BeautifulSoup
from nltk.corpus import stopwords
from nltk.stem import PorterStemmer
import nltk

def setup_nltk():
    """Setup NLTK by downloading required data."""
    try:
        print("Starting NLTK setup...")
        nltk.download('stopwords', quiet=True)
        print("NLTK setup completed successfully")
    except Exception as e:
        print(f"Error during NLTK setup: {e}")

async def scrape_page(page_num: int, all_jobs: List[Dict]) -> None:
    """
    Scrapes job postings from Adobe's careers page using Puppeteer.

    Args:
        page_num: Page number to scrape
        all_jobs: List to store found jobs
    """
    print(f"\nStarting to scrape page {page_num}...")
    try:
        browser = await launch(options={'timeout': 120000})
        page = await browser.newPage()
        await page.goto(f'https://careers.adobe.com/us/en/search-results?offset={page_num}', timeout=120000)

        # Wait for the page to load completely
        await page.waitForSelector('.jobs-list-item', timeout=120000)
        html = await page.content()
        # Close all pages before closing the browser
        await asyncio.gather(*[page.close() for page in await browser.pages()])
        await browser.close()

        soup = BeautifulSoup(html, 'html.parser')
        jobs = soup.find_all('li', class_='jobs-list-item')

        print(f"Found {len(jobs)} jobs on page {page_num}")

        for job in jobs:
            try:
                # Extract relevant job information
                role_elem = job.find('a', {'data-ph-id': re.compile(r'ph-page-element-page15-iK3vh8')})
                role = role_elem.find('div', class_='job-title').text.strip() if role_elem else None
                role_url = role_elem['href'] if role_elem else None

                req_id_elem = job.find('a', {'data-ph-id': re.compile(r'ph-page-element-page15-iK3vh8')})
                req_id = req_id_elem['data-ph-at-job-id-text'] if req_id_elem else None

                location_elem = job.find('span', {'data-ph-id': re.compile(r'ph-page-element-page15-4l6vaX')})
                if location_elem:
                    location_value_elem = location_elem.find('span', class_='job-location')
                    if location_value_elem:
                        location = location_value_elem.text.strip()
                        # Trim "Location" and extra whitespace
                        location = location.replace("Location", "").strip()
                    else:
                        location = None
                else:
                    location = None

                if role and role_url and req_id and location and "United States" in location:
                    print(f"\nFound matching job:")
                    print(f"Role: {role}")
                    print(f"Location: {location}")
                    print(f"Req ID: {req_id}")
                    print(f"URL: {role_url}")

                    all_jobs.append({
                        "role": role,
                        "role_url": role_url,
                        "req_id": req_id,
                        "location": location
                    })

            except Exception as e:
                print(f"Error processing job data: {e}")
                continue

        print(f"Successfully processed page {page_num}")
    except Exception as e:
        print(f"Error scraping page {page_num}: {e}")

async def scrape_job_description(job):
    """
    Scrapes the job description from the given job URL.

    Args:
        job: Job data dictionary containing the role_url.

    Returns:
        str: Job description text, or None if an error occurs.
    """
    try:
        browser = await launch()
        page = await browser.newPage()
        await page.goto(job['role_url'])
        await page.waitForSelector('div[data-ph-at-id="jobdescription-text"]')
        description_element = await page.querySelector('div[data-ph-at-id="jobdescription-text"]')
        description = await page.evaluate('(element) => element.textContent', description_element)
        await browser.close()
        return description
    except Exception as e:
        print(f"Error scraping job description for {job['role']} at {job['role_url']}: {e}")
        return None

def calculate_match_score(job_description, resume_text):
    """
    Calculates the match score between the job description and resume.

    Args:
        job_description: Job description text.
        resume_text: Resume text.

    Returns:
        float: Match score as a percentage.
    """
    # Preprocess text (lowercase, remove stop words, stemming)
    ps = PorterStemmer()
    stop_words = set(stopwords.words('english'))
    job_keywords = set([ps.stem(word) for word in job_description.lower().split() if word not in stop_words])
    resume_keywords = set([ps.stem(word) for word in resume_text.lower().split() if word not in stop_words])

    # Calculate match score
    common_keywords = job_keywords.intersection(resume_keywords)
    match_score = len(common_keywords) / len(job_keywords) * 100 if job_keywords else 0
    return match_score

async def match_jobs_to_resume(all_jobs, resume_text):
    """
    Matches the job roles to the resume and calculates match scores.

    Args:
        all_jobs: List of job data dictionaries.
        resume_text: Resume text.

    Returns:
        list: List of dictionaries containing job data and match scores.
    """
    matched_jobs = []
    for job in all_jobs:
        job_description = await scrape_job_description(job)
        if job_description:
            match_score = calculate_match_score(job_description, resume_text)
            job['match_score'] = f"{match_score:.2f}%"
            matched_jobs.append(job)
    return matched_jobs

def main():
    """
    Main function to execute the scraping, matching, and saving process.
    """
    print("Starting the scraping process...")
    setup_nltk()

    print("Initializing job list...")
    all_jobs = []

    print("Beginning to scrape pages...")
    loop = asyncio.get_event_loop()
    tasks = [scrape_page(page_num, all_jobs) for page_num in range(0, 60, 10)]
    loop.run_until_complete(asyncio.gather(*tasks))

    print(f"\nScraping completed. Found {len(all_jobs)} total jobs")

    if all_jobs:
        # Save initial scraping results
        timestamp = datetime.now().strftime("%d%m%Y")
        output_file = f"adobe_jobs_{timestamp}.csv"
        try:
            with open(output_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=["role", "role_url", "req_id", "location"])
                writer.writeheader()
                writer.writerows(all_jobs)
            print(f"\nInitial scraping results saved to {output_file}")
        except Exception as e:
            print(f"Error saving initial scraping results: {e}")

        # Match jobs to resume and save results
        with open('resume.txt', 'r') as f:
            resume_text = f.read()

        matched_jobs = loop.run_until_complete(match_jobs_to_resume(all_jobs, resume_text))

        if matched_jobs:
            output_file = f"adobe_role_matched_{timestamp}.csv"
            try:
                with open(output_file, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.DictWriter(f, fieldnames=["role", "role_url", "req_id", "location", "match_score"])
                    writer.writeheader()
                    writer.writerows(matched_jobs)
                print(f"\nMatched jobs saved to {output_file}")
            except Exception as e:
                print(f"Error saving matched jobs: {e}")
        else:
            print("No matching jobs found to save")
    else:
        print("No jobs were found to save")

if __name__ == "__main__":
    main()