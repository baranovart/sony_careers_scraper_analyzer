import csv
import os
import argparse
from datetime import datetime
import requests
from bs4 import BeautifulSoup
import nltk
from nltk.corpus import stopwords
from nltk.stem import PorterStemmer
import re
import pandas as pd
import math

# Ensure required NLTK resources are available
nltk.download("stopwords")

def get_working_dir():
    return os.path.abspath(os.path.dirname(__file__))

def scrape_sony_careers(all_jobs, keywords_file):
    """
    Fetches job postings via the API and filters out US-based jobs that
    have a role title match in the top 20% when compared to keywords in keywords.txt.
    Also extracts department and first_published date.
    """
    # Read keywords from the file
    keywords_path = os.path.join(get_working_dir(), keywords_file)
    try:
        with open(keywords_path, "r", encoding="utf-8") as f:
            keywords = [kw.strip().lower() for kw in f.readlines() if kw.strip()]
    except FileNotFoundError:
        print("Keywords file not found.")
        return
    
    url = "https://boards-api.greenhouse.io/v1/boards/sonyinteractiveentertainmentglobal/jobs"
    try:
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            jobs_df = pd.DataFrame(data['jobs'])
            jobs_df['location_name'] = jobs_df['location'].apply(lambda x: x['name'] if isinstance(x, dict) else '')
            # Filter for US-based jobs
            filtered_jobsdf = jobs_df[jobs_df['location_name'].str.contains('United States', case=False, na=False)]
            
            # Calculate match score for each job based on role title and keywords
            job_list = []
            for _, row in filtered_jobsdf.iterrows():
                role_title = row['title'].lower()
                match_scores = []
                for kw in keywords:
                    if kw in role_title:
                        # Score: length of the keyword divided by length of role title
                        match_scores.append(len(kw) / len(role_title))
                if match_scores:
                    best_match_score = max(match_scores)
                    job_list.append((row, best_match_score))
            
            if not job_list:
                print("No jobs matched the keywords in the role title.")
                return
            
            # Determine the threshold for top 20% match score
            scores = [score for (_, score) in job_list]
            scores_sorted = sorted(scores)
            n = len(scores_sorted)
            k = math.ceil(0.2 * n)  # number of jobs in the top 20%
            cutoff_index = n - k  # index for the cutoff in ascending sorted order
            threshold = scores_sorted[cutoff_index]
            
            # Only add jobs with match score >= threshold
            for row, score in job_list:
                if score >= threshold:
                    # Extract department from metadata (using "Career Page - Department") if available
                    department = "N/A"
                    metadata = row.get('metadata', [])
                    for item in metadata:
                        if item.get('name') == "Career Page - Department" and item.get('value'):
                            department = item.get('value')
                            break
                    
                    job_dict = {
                        "role": row['title'],
                        "role_url": row['absolute_url'],
                        "department": department,
                        "location": row['location_name'],
                        "first_published": row.get("first_published", "N/A"),
                        "description": ""  # Placeholder; to be updated later
                    }
                    all_jobs.append(job_dict)
            print(f"API call successful: Found {len(all_jobs)} US-based jobs after keyword filtering.")
        else:
            print(f"Failed to retrieve data, status code {response.status_code}")
    except Exception as e:
        print(f"Error fetching API data: {e}")

def scrape_job_descriptions(jobs, output_folder):
    """
    Scrapes job descriptions from each job's URL and saves the text to a file.
    The job dict is updated with the description.
    """
    os.makedirs(output_folder, exist_ok=True)
    
    for job in jobs:
        role_filename = re.sub(r'[<>:"/\\|?*]', '_', job["role"])[:50] + ".txt"
        filepath = os.path.join(output_folder, role_filename)
        
        try:
            response = requests.get(job["role_url"])
            response.raise_for_status()
            soup = BeautifulSoup(response.content, "html.parser")
            description_element = soup.find("div", class_="job__description")
            if description_element:
                job_description = description_element.get_text(separator='\n', strip=True)
                job["description"] = job_description  # Store the description
                with open(filepath, "w", encoding="utf-8") as f:
                    f.write(job_description)
                print(f"Scraped: {job['role']}")
        except requests.exceptions.RequestException as e:
            print(f"Error fetching job description: {e}")

def analyze_resume(resume_file, jobs):
    """
    Analyzes the resume against each job's description by comparing text overlap,
    calculates a fit_score for each job, and sorts the jobs by fit_score.
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
        return []
    
    stop_words = set(stopwords.words("english"))
    stemmer = PorterStemmer()
    
    for job in jobs:
        job_text = job.get("description", "")
        if job_text:
            resume_words = {stemmer.stem(word) for word in re.findall(r'\b\w+\b', resume_text.lower()) if word not in stop_words}
            job_words = {stemmer.stem(word) for word in re.findall(r'\b\w+\b', job_text.lower()) if word not in stop_words}
            fit_score = (len(resume_words & job_words) / len(job_words)) * 100 if job_words else 0
            job["fit_score"] = fit_score
        else:
            job["fit_score"] = 0
    
    jobs.sort(key=lambda x: x["fit_score"], reverse=True)
    return jobs

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-r", "--resume", default="resume.txt", help="Path to the resume file")
    parser.add_argument("-k", "--keywords", default="keywords.txt", help="Keywords file (one keyword/phrase per line)")
    args = parser.parse_args()
    
    # Rename output directory to "psn_output"
    output_folder = os.path.join(get_working_dir(), "psn_output")
    os.makedirs(output_folder, exist_ok=True)
    
    print("Fetching jobs via API...")
    all_jobs = []
    scrape_sony_careers(all_jobs, args.keywords)
    print(f"Found {len(all_jobs)} total jobs after initial filtering")
    
    if not all_jobs:
        print("No jobs to process after keyword filtering.")
        return
    
    print("\nScraping job descriptions...")
    scrape_job_descriptions(all_jobs, output_folder)
    
    print("\nAnalyzing resume...")
    matched_jobs = analyze_resume(args.resume, all_jobs)
    
    if matched_jobs:
        csv_path = os.path.join(output_folder, "filtered_jobs.csv")
        # Write only the selected fields to CSV
        fieldnames = ["role", "role_url", "department", "location", "first_published", "fit_score"]
        with open(csv_path, "w", newline="", encoding="utf-8") as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows([{k: job.get(k, "") for k in fieldnames} for job in matched_jobs])
        print(f"\nSaved {len(matched_jobs)} matching jobs to {csv_path}")
    else:
        print("No matching jobs found.")

if __name__ == "__main__":
    main()
