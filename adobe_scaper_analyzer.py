import csv
import asyncio
import re  # Import the re module
from typing import List, Dict

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
        browser = await launch(options={'timeout': 120000})  # Increased timeout to 120 seconds
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

def main():
    """
    Main function to execute the scraping and analysis process.
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
        output_file = "adobe_jobs.csv"
        try:
            with open(output_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=["role", "role_url", "req_id", "location"])
                writer.writeheader()
                writer.writerows(all_jobs)
            print(f"\nResults saved to {output_file}")
        except Exception as e:
            print(f"Error saving results: {e}")
    else:
        print("No jobs were found to save")

if __name__ == "__main__":
    main()