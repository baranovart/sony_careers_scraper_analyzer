import csv
import os
import re
import asyncio
from datetime import datetime
from bs4 import BeautifulSoup
from pyppeteer import launch
import nltk
from nltk.corpus import stopwords
from nltk.stem import PorterStemmer
from nltk.tokenize import word_tokenize

# Ensure required NLTK resources are available
nltk.download("stopwords", quiet=True)
nltk.download("punkt", quiet=True)
nltk.download('punkt_tab', quiet=True)

OUTPUT_FOLDER = "dropbox_output"

# Ensure output folder exists and clean old files
def setup_output_folder():
    if not os.path.exists(OUTPUT_FOLDER):
        os.makedirs(OUTPUT_FOLDER)
    else:
        for file in os.listdir(OUTPUT_FOLDER):
            file_path = os.path.join(OUTPUT_FOLDER, file)
            if os.path.isfile(file_path):
                os.remove(file_path)

def filter_us_jobs(jobs):
    us_jobs = []
    non_us_keywords = ["POLAND", "CANADA", "UK", "AUSTRALIA", "GERMANY", "FRANCE", "INDIA"]
    for job in jobs:
        location = job["location"].upper()
        # Extract only the first location if multiple are listed
        primary_location = location.split(":")[0].strip()
        if re.search(r"\bUS\b|\bUNITED STATES\b", primary_location) and not any(country in primary_location for country in non_us_keywords):
            us_jobs.append(job)
    return us_jobs

async def fetch_jobs():
    """Fetches job postings from Dropbox's careers page using Pyppeteer."""
    browser = await launch(headless=True, args=["--no-sandbox"])
    page = await browser.newPage()
    await page.goto("https://jobs.dropbox.com/all-jobs?", timeout=90000)

    # Scroll and wait for content to load fully
    for _ in range(5):
        await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        await asyncio.sleep(3)

    try:
        await page.waitForSelector(".open-positions__listing", timeout=60000)
    except Exception:
        print("Job listings did not load properly. Retrying...")
        await asyncio.sleep(5)
        await page.reload()
        await asyncio.sleep(5)

    content = await page.content()
    soup = BeautifulSoup(content, 'html.parser')
    listing_elements = soup.select('li.open-positions__listing')
    print(f"Found {len(listing_elements)} listing elements with BeautifulSoup")

    job_listings = []
    for listing in listing_elements:
        try:
            location = listing.get('data-location', '').strip()
            link_element = listing.select_one('a.open-positions__listing-link')
            if link_element:
                link = link_element.get('href', '').strip()
                if not link.startswith('http'):
                    link = 'https://jobs.dropbox.com' + link
                title_element = link_element.select_one('.open-positions__listing-title')
                title = title_element.text.strip() if title_element else ''
                job_listings.append({'title': title, 'location': location, 'link': link})
                print(f"Extracted job: {title} | {location}")
        except Exception as e:
            print(f"Error parsing job listing: {e}")

    await browser.close()
    us_jobs = filter_us_jobs(job_listings)
    print(f"US-based jobs found: {len(us_jobs)}")
    return us_jobs

async def scrape_job_details(job):
    """Scrapes job details from individual job pages using Pyppeteer."""
    job_file = os.path.join(OUTPUT_FOLDER, f"{re.sub(r'[^a-zA-Z0-9]', '_', job['title'])}.txt")
    
    if os.path.exists(job_file):
        with open(job_file, "r", encoding="utf-8") as f:
            return {"title": job['title'], "description": f.read()}
    
    try:
        browser = await launch(headless=True, args=["--no-sandbox"])
        page = await browser.newPage()
        await page.goto(job["link"], timeout=90000)

        for _ in range(5):
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await asyncio.sleep(3)

        await page.waitForSelector(".job-description-details, .jc03-content", timeout=60000)
        content = await page.content()
        soup = BeautifulSoup(content, 'html.parser')
        description_element = soup.select_one(".job-description-details") or soup.select_one(".jc03-content")
        description = description_element.get_text(" ").strip() if description_element else ""

        with open(job_file, "w", encoding="utf-8") as f:
            f.write(description)

        await browser.close()
        return {"title": job["title"], "description": description}
    
    except Exception as e:
        print(f"Error fetching job details for {job['title']}: {e}")
        return None

async def main():
    setup_output_folder()
    print("Fetching Dropbox job listings...")
    jobs = await fetch_jobs()
    print(f"Total jobs found: {len(jobs)}")
    
    if not jobs:
        print("No jobs found. Exiting.")
        return
    
    timestamp = datetime.now().strftime("%d%m%Y")
    output_file = f"dropbox_matched_jobs_{timestamp}.csv"
    
    with open("resume.txt", "r", encoding="utf-8") as f:
        resume_text = f.read()

    matched_jobs = []
    for job in jobs:
        print(f"Scraping details for: {job['title']}")
        job_details = await scrape_job_details(job)
        if job_details:
            match_score = len(set(job_details["description"].lower().split()) & set(resume_text.lower().split())) / max(len(set(resume_text.lower().split())), 1) * 100
            matched_jobs.append({
                "title": job_details["title"],
                "location": job["location"],
                "link": job["link"],
                "match_score": round(match_score, 2)
            })
    
    with open(output_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["title", "location", "link", "match_score"])
        writer.writeheader()
        writer.writerows(matched_jobs)
    
    print(f"Scraped details for {len(matched_jobs)} jobs. Results saved to {output_file}.")

if __name__ == "__main__":
    asyncio.run(main())
