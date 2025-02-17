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

# Ensure required NLTK resources are available
nltk.download("stopwords")

def get_working_dir():
    """Returns the absolute path of the script's working directory."""
    return os.path.abspath(os.path.dirname(__file__))

def scrape_sony_careers(page_num, all_jobs):
    """Scrapes job postings from Sony Interactive Entertainment's Greenhouse job board."""
    base_url = f"https://job-boards.greenhouse.io/sonyinteractiveentertainmentglobal?page={page_num}"
    
    try:
        response = requests.get(base_url)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, "html.parser")
        job_post_sections = soup.find_all("div", class_="job-posts")
        
        for section in job_post_sections:
            department_element = section.find("div", class_="job-posts--department-path")
            department = department_element.text.strip() if department_element else "N/A"
            
            job_rows = section.find_all("tr", class_="job-post")
            for row in job_rows:
                link = row.find("a")
                if link:
                    role = link.find("p", class_="body--medium").text.strip()
                    role_url = link["href"]
                    location_element = link.find("p", class_="body__secondary")
                    location = location_element.text.strip() if location_element else ""
                    
                    if "United States" in location or "US" in location or "Remote - US" in location:
                        all_jobs.append({
                            "role": role, 
                            "role_url": role_url, 
                            "department": department,
                            "location": location
                        })
    except requests.exceptions.RequestException as e:
        print(f"Error fetching URL: {e}")

def filter_jobs_by_keywords(all_jobs, keywords_file):
    """Filters jobs based on keywords found in the provided keywords file with stricter matching."""
    keywords_path = os.path.join(get_working_dir(), keywords_file)
    
    try:
        with open(keywords_path, "r", encoding="utf-8") as f:
            # Split by newline instead of comma for more precise control
            keywords = [keyword.strip().lower() for keyword in f.readlines() if keyword.strip()]
    except FileNotFoundError:
        print("Keywords file not found.")
        return []
    
    filtered_jobs = []
    for job in all_jobs:
        role_lower = job["role"].lower()
        department_lower = job["department"].lower()
        
        # Check for exact phrase matches in both role and department
        for keyword in keywords:
            if (keyword in role_lower or keyword in department_lower):
                # Calculate match score based on keyword length vs. total length
                match_score = len(keyword) / len(role_lower)
                job["match_score"] = match_score
                filtered_jobs.append(job)
                break
    
    # Sort by match score and take top 10 matches
    filtered_jobs.sort(key=lambda x: x["match_score"], reverse=True)
    return filtered_jobs[:10]

def scrape_job_descriptions(jobs, output_folder):
    """Scrapes job descriptions and saves them as text files."""
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
                description_text = (
                    f"Role: {job['role']}\n"
                    f"Department: {job['department']}\n"
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
    """Analyzes a resume against job descriptions."""
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
                resume_words = {stemmer.stem(word) for word in re.findall(r'\b\w+\b', resume_text.lower()) 
                              if word not in stop_words}
                job_words = {stemmer.stem(word) for word in re.findall(r'\b\w+\b', job_text.lower()) 
                           if word not in stop_words}
                fit_score = (len(resume_words & job_words) / len(job_words)) * 100 if job_words else 0
                matches.append((filename, fit_score))
    
    # Sort by fit score and print top matches
    matches.sort(key=lambda x: x[1], reverse=True)
    print("\nTop matches for your resume:")
    for filename, score in matches:
        print(f"{filename}: {int(score)}% match")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-r", "--resume", required=True, help="Path to the resume file")
    parser.add_argument("-k", "--keywords", default="keywords.txt", help="Keywords file (one keyword/phrase per line)")
    args = parser.parse_args()
    
    output_folder = os.path.join(get_working_dir(), "output")
    os.makedirs(output_folder, exist_ok=True)
    
    print("Scraping jobs...")
    all_jobs = []
    for page_num in range(1, 6):
        scrape_sony_careers(page_num, all_jobs)
    print(f"Found {len(all_jobs)} total jobs")
    
    filtered_jobs = filter_jobs_by_keywords(all_jobs, args.keywords)
    
    if filtered_jobs:
        csv_path = os.path.join(output_folder, "filtered_jobs.csv")
        with open(csv_path, "w", newline="", encoding="utf-8") as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=["role", "role_url", "department", "location", "match_score"])
            writer.writeheader()
            writer.writerows(filtered_jobs)
        print(f"\nSaved {len(filtered_jobs)} matching jobs to {csv_path}")
        
        print("\nScraping job descriptions...")
        scrape_job_descriptions(filtered_jobs, output_folder)
    else:
        print("No matching jobs found.")
    
    print("\nAnalyzing resume...")
    analyze_resume(args.resume, output_folder)

if __name__ == "__main__":
    main()