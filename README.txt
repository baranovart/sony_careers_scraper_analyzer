Sony, Dropbox and Adobe Scraper Analyzer

This script scrapes job posting role names from PSN's Greenhouse and Adobe job boards, filters them based on keywords, downloads job descriptions, and analyzes how well a resume matches the scraped jobs.

Features

Scrapes up to 5 pages of job listings.

Filters jobs based on a provided list of keywords.

Saves job descriptions in text files.

Compares a resume against job descriptions for relevance scoring. 
Create keywords.txt as a comma separated list of keywords. One keyword per line, no comas. 


Python 3.7+

Required Python libraries:

requests

beautifulsoup4

nltk

Install dependencies with:

pip install -r requirements.txt

Usage

Run the script using:

python3 psn_scraper_analyzer.py -r resume.txt -k keywords.txt
python3 adobe_scraper_analyzer.py -r resume.txt -k keywords.txt

-r / --resume (Required): Path to the resume text file.

-k / --keywords (Optional): Path to the keywords file (default: keywords.txt).

Output

output/filtered_jobs.csv: Filtered job listings.

output/: Contains job descriptions.

The script prints job match scores for the resume.

Notes

Ensure keywords.txt contains one role name per line

NLTK stopwords are downloaded automatically.

License

This project is licensed under the Apache License 2.0.

