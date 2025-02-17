import csv
import os
import re

import requests
from bs4 import BeautifulSoup
from nltk.corpus import stopwords
from nltk.stem import PorterStemmer
import nltk

nltk.download('stopwords')


def get_working_dir():
    """Returns the absolute path of the script's working directory."""
    return os.path.abspath(os.path.dirname(__file__))


def scrape_adobe_careers(page_num, all_jobs):
    """
    Scrapes job postings from Adobe's career site.
    """
    base_url = f"https://careers.adobe.com/us/en/search-results?from={page_num}&s=1"

    try:
        response = requests.get(base_url)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, "html.parser")
        job_postings = soup.find_all("tr",
                                     attrs={"data-ph-id": re.compile(r"^ph-page-element-page\d+")})

        if not job_postings:
            print(f"Warning: No job postings found on page {page_num}. Check the HTML structure.")

        for job_posting in job_postings:
            location_element = job_posting.find("td", attrs={"data-ph-at-job-location-text": True})
            if not location_element:
                print("Warning: Location element not found in job posting. Skipping...")
                continue
            location = location_element.text.strip()

            if "United States" in location or "US" in location:
                role_element = job_posting.find("a", attrs={"data-ph-at-job-title-text": True})
                if not role_element:
                    print("Warning: Role element not found in job posting. Skipping...")
                    continue
                role = role_element.text.strip()
                role_url = "https://careers.adobe.com" + role_element['href']
                req_id = job_posting["data-ph-id"].split('-')[-1]

                print(f"Role: {role}")
                print(f"URL: {role_url}")
                print(f"Req ID: {req_id}")
                print(f"Location: {location}")
                print("-" * 20)  # Separator between job postings

                all_jobs.append({
                    "role": role,
                    "role_url": role_url,
                    "req_id": req_id,
                    "location": location
                })

    except requests.exceptions.RequestException as e:
        print(f"Error fetching URL: {e}")


def filter_jobs_by_keywords(all_jobs, keywords_file):
    """
    Filters jobs based on keywords found in the provided keywords file.
    """
    keywords_path = os.path.join(get_working_dir(), keywords_file)

    try:
        with open(keywords_path, "r", encoding="utf-8") as f:
            # Split by newline instead of comma for more precise control
            keywords = [
                keyword.strip().lower() for keyword in f.readlines()
                if keyword.strip()
            ]
    except FileNotFoundError:
        print("Keywords file not found.")
        return

    filtered_jobs = [] 
    for job in all_jobs:
        role_lower = job["role"].lower()

        # Check for exact phrase matches in both role and department
        for keyword in keywords:
            if keyword in role_lower:
                # Calculate match score based on keyword length vs. total length
                match_score = len(keyword) / len(role_lower)
                job["match_score"] = match_score
                filtered_jobs.append(job)
                break

    # Sort by match score and take top 10 matches
    filtered_jobs.sort(key=lambda x: x["match_score"], reverse=True)
    return filtered_jobs[:10]


def scrape_job_descriptions(jobs, output_folder):
    """
    Scrapes job descriptions and saves them as text files.
    """
    os.makedirs(output_folder, exist_ok=True)

    for job in jobs:
        role_filename = re.sub(r'[<>:"/\\|?*]', '_', job["role"])[:50] + ".txt"
        filepath = os.path.join(output_folder, role_filename)

        try:
            response = requests.get(job["role_url"])
            response.raise_for_status()
            soup = BeautifulSoup(response.content, "html.parser")
            description_element = soup.find("div", class_="job-description")
            if description_element:
                description_text = (
                    f"Role: {job['role']}\n"
                    f"Req ID: {job['req_id']}\n"
                    f"Location: {job['location']}\n"
                    f"Match Score: {job['match_score']:.2%}\n\n"
                    f"{description_element.get_text(separator='\n', strip=True)}\n\n"
                    f"URL: {job['role_url']}"
                )
                with open(filepath, "w", encoding="utf-8") as f:
                    f.write(description_text)
                print(f"Scraped: {job['role']}")
        except requests.exceptions.RequestException as e:
            print(f"Error fetching job description: {e}")


def analyze_resume(resume_file, job_descriptions_dir):
    """
    Analyzes a resume against job descriptions.
    """
    resume_path = os.path.join(get_working_dir(), resume_file)

    def read_file(file_path):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return f.read()
        except Exception as e:
            print(f"Error reading {file_path}: {e}")
            return ""

    resume_text = read_file(resume_path)
    if not resume_text:
        return

    stop_words = set(stopwords.words("english"))
    stemmer = PorterStemmer()

    matches = []
    for filename in os.listdir(job_descriptions_dir):
        if filename.endswith(".txt"):
            job_desc_path = os.path.join(job_descriptions_dir, filename)
            job_text = read_file(job_desc_path)

            if job_text:
                resume_words = {
                    stemmer.stem(word)
                    for word in re.findall(r'\b\w+\b', resume_text.lower())
                    if word not in stop_words
                }
                job_words = {
                    stemmer.stem(word)
                    for word in re.findall(r'\b\w+\b', job_text.lower())
                    if word not in stop_words
                }
                fit_score = (len(resume_words & job_words) / len(job_words)
                             ) * 100 if job_words else 0
                matches.append((filename, fit_score))

    # Sort by fit score and print top matches
    matches.sort(key=lambda x: x, reverse=True)
    print("\nTop matches for your resume:")
    for filename, score in matches:
        print(f"{filename}: {int(score)}% match")


def main():
    """
    Main function to execute the scraping and analysis process.
    """
    #... (rest of the main function remains the same)
    print("Scraping jobs...")
    all_jobs = []
    for page_num in range(0, 60, 10):  # Pages 1-5
        scrape_adobe_careers(page_num, all_jobs)
    print(f"Found {len(all_jobs)} total jobs")

    #... (rest of the main function remains the same)


if __name__ == "__main__":
    main()