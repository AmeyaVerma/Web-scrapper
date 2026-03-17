import os
import json
import smtplib
from email.message import EmailMessage
import requests
from google import genai

# --- CONFIGURATION & SECRETS ---
APPS_SCRIPT_URL = os.getenv("APPS_SCRIPT_URL")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
FIRECRAWL_API_KEY = os.getenv("FIRECRAWL_API_KEY")
EMAIL_SENDER = os.getenv("EMAIL_SENDER")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
GOOGLE_SHEET_URL = os.getenv("GOOGLE_SHEET_URL", "Link not provided in secrets.")
EMAIL_RECEIVER = "ameyaverma1977@gmail.com"

# --- TARGET DATA ---
TARGET_COMPANIES = {
    "IBM": "https://www.ibm.com/careers",
    "Barclays": "https://search.jobs.barclays",
    "Oracle": "https://careers.oracle.com",
    "American Express": "https://www.americanexpress.com/en-us/careers",
    "Meesho": "https://careers.meesho.com",
    "JP Morgan": "https://www.jpmorganchase.com/careers",
    "Zepto": "https://www.zeptonow.com/careers",
    "Databricks": "https://www.databricks.com/company/careers",
    "Nvidia": "https://www.nvidia.com/en-us/about-nvidia/careers",
    "Optum": "https://careers.unitedhealthgroup.com",
    "Coinbase": "https://www.coinbase.com/careers",
    "Morgan Stanley": "https://www.morganstanley.com/careers",
    "Mastercard": "https://careers.mastercard.com",
    "Visa": "https://www.visa.com/careers",
    "Stripe": "https://stripe.com/jobs",
    "Juspay": "https://juspay.io/careers",
    "Razorpay": "https://razorpay.com/jobs",
    "CRED": "https://careers.cred.club",
    "Nike": "https://jobs.nike.com"
}

# --- TEMPORARY TESTING FILTERS ---
TARGET_EXPERIENCE = "Any experience level from 0 to 5 years."
TARGET_ROLES = "Any tech, engineering, data, or software role."
TARGET_LOCATION = "Any location."

# Setup New Gemini Client
client = genai.Client(api_key=GEMINI_API_KEY)

def scrape_page(url):
    """Extracts raw markdown using Firecrawl with the updated V1 API format."""
    headers = {
        "Authorization": f"Bearer {FIRECRAWL_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "url": url, 
        "formats": ["markdown"], 
        "onlyMainContent": True
    }
    
    try:
        response = requests.post("https://api.firecrawl.dev/v1/scrape", headers=headers, json=payload)
        if response.status_code == 200:
            return response.json().get("data", {}).get("markdown", "")
        else:
            print(f"    -> Firecrawl Error: Status Code {response.status_code}")
            return ""
    except Exception as e:
        print(f"    -> Request Error: {e}")
        return ""

def extract_jobs_with_ai(markdown_content):
    """Filters markdown for relevant tech jobs using the new GenAI SDK."""
    prompt = f"""
    You are an expert tech recruiter. Review the following career page markdown.
    Extract job postings that match these criteria:
    - Experience Level: {TARGET_EXPERIENCE}
    - Fields: {TARGET_ROLES}
    - Location: {TARGET_LOCATION}
    
    Return ONLY a valid JSON array of objects with keys: "Job Name", "Apply link".
    If no jobs match, return an empty array [].
    Do not include markdown formatting like ```json in the output, just the raw JSON array.
    
    Markdown Content:
    {markdown_content}
    """
    try:
        # NEW SDK GENERATION CALL
        response = client.models.generate_content(
            model='gemini-1.5-flash',
            contents=prompt
        )
        
        json_str = response.text.strip()
        if json_str.startswith("```json"):
            json_str = json_str.removeprefix("```json").removesuffix("```").strip()
        elif json_str.startswith("```"):
            json_str = json_str.removeprefix("```").removesuffix("```").strip()
            
        return json.loads(json_str)
    except Exception as e:
        print(f"    -> AI Extraction error or invalid JSON: {e}")
        return []

def update_google_sheet(all_company_jobs):
    """Sends a POST request to our Google Apps Script Webhook."""
    payload = {"jobs_data": all_company_jobs}
    try:
        response = requests.post(APPS_SCRIPT_URL, json=payload)
        if response.status_code == 200:
            print("Successfully updated Google Sheet.")
        else:
            print(f"Failed to update Google Sheet. Status Code: {response.status_code}")
            print(f"Response: {response.text}")
    except Exception as e:
        print(f"Failed to connect to Google Webhook: {e}")

def send_notification_email():
    """Emails you when the process is done, including the sheet link."""
    msg = EmailMessage()
    msg['Subject'] = "Your Daily Tech Job Scraper Update is Ready!"
    msg['From'] = EMAIL_SENDER
    msg['To'] = EMAIL_RECEIVER
    
    body = f"""Hello,

Your AI job scraper has finished checking all the company career pages.
Open your Google Sheet below to view the updated list and apply for roles!

Access your database here: 
{GOOGLE_SHEET_URL}

Happy hunting!
"""
    msg.set_content(body)

    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
            smtp.login(EMAIL_SENDER, EMAIL_PASSWORD)
            smtp.send_message(msg)
            print("Successfully sent notification email.")
    except Exception as e:
        print(f"Failed to send email: {e}")

def main():
    all_company_jobs = {}
    print("Starting Job Scraper Pipeline...\n")
    
    for company, url in TARGET_COMPANIES.items():
        print(f"Processing {company}...")
        markdown = scrape_page(url)
        
        if markdown:
            jobs = extract_jobs_with_ai(markdown)
            if jobs: 
                print(f"    -> Success! Found {len(jobs)} matching jobs.")
                all_company_jobs[company] = jobs
            else:
                print("    -> Found 0 matching jobs.")
        else:
            print("    -> Failed to retrieve markdown or page is empty.")
            
    print("\nSending data to Google Sheet Webhook...")
    if all_company_jobs:
        update_google_sheet(all_company_jobs)
    else:
        print("No jobs found across any companies. Skipping Sheet update to preserve previous data.")
    
    print("\nSending Notification Email...")
    send_notification_email()
    print("\nComplete!")

if __name__ == "__main__":
    main()
