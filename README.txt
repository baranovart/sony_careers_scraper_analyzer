Sony Scraper Analyzer

This script scrapes job postings from Sony Interactive Entertainment's Greenhouse job board, filters them based on keywords, downloads job descriptions, and analyzes how well a resume matches the scraped jobs.

Features

Scrapes up to 5 pages of job listings.

Filters jobs based on a provided list of keywords.

Saves job descriptions in text files.

Compares a resume against job descriptions for relevance scoring. 
Create keywords.txt as a comma separated list of keywords. Sample promt for keyword generation provided in sample keywords.txt file
Create .txt version of your resume

Requirements

Python 3.7+

Required Python libraries:

requests

beautifulsoup4

nltk

Install dependencies with:

pip install -r requirements.txt

Usage

Run the script using:

python scraper_analyzer_update.py -r resume.txt -k keywords.txt

-r / --resume (Required): Path to the resume text file.

-k / --keywords (Optional): Path to the keywords file (default: keywords.txt).

Output

output/filtered_jobs.csv: Filtered job listings.

output/: Contains job descriptions.

The script prints job match scores for the resume.

Notes

Ensure keywords.txt contains comma-separated keywords.

NLTK stopwords are downloaded automatically.

License

This project is licensed under the Apache License 2.0.

