import os
import json
import smtplib
from email.message import EmailMessage
import requests
import google.generativeai as genai

# --- CONFIGURATION & SECRETS ---
APPS_SCRIPT_URL = os.getenv("APPS_SCRIPT_URL")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
FIRECRAWL_API_KEY = os.getenv("FIRECRAWL_API_KEY")
EMAIL_SENDER = os.getenv("EMAIL_SENDER")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
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

TARGET_EXPERIENCE = "Fresher, Internship, New graduate, or up to 1 year of experience"
TARGET_ROLES = "Data Science, Data Analyst, Data Handling, Machine Learning, Artificial Intelligence, Software Development, AWS, Power BI, Tableau."
TARGET_LOCATION = "Hybrid, Onsite, Remote anywhere in India, or Remote anywhere in the world."

# Setup Gemini
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

def scrape_page(url):
    """Extracts raw markdown using Firecrawl."""
    headers = {"Authorization": f"Bearer {FIRECRAWL_API_KEY}", "Content-Type": "application/json"}
    payload = {"url": url, "pageOptions": {"onlyMainContent": True}}
    response = requests.post("https://api.firecrawl.dev/v1/scrape", headers=headers, json=payload)
    if response.status_code == 200:
        return response.json().get("data", {}).get("markdown", "")
    return ""

def extract_jobs_with_ai(markdown_content):
    """Filters markdown for relevant tech jobs, specifically highlighting non-desk or travel-heavy roles."""
    prompt = f"""
    You are an expert tech recruiter. Review the following career page markdown.
    Extract job postings that match these criteria:
    - Experience Level: {TARGET_EXPERIENCE}
    - Fields: {TARGET_ROLES}
    - Location: {TARGET_LOCATION}
    
    Prioritize or look closely for roles that break the mold of a traditional 9-to-5 desk job, such as those involving travel, field engineering, or dynamic environments, alongside the standard tech roles.
    
    Return ONLY a valid JSON array of objects with keys: "Job Name", "Apply link".
    If no jobs match, return an empty array [].
    
    Markdown Content:
    {markdown_content}
    """
    try:
        response = model.generate_content(prompt)
        json_str = response.text.strip().removeprefix("```json").removesuffix("```").strip()
        return json.loads(json_str)
    except Exception as e:
        print(f"AI Extraction error: {e}")
        return []

def update_google_sheet(all_company_jobs):
    """Sends a POST request to our Google Apps Script Webhook."""
    payload = {"jobs_data": all_company_jobs}
    response = requests.post(APPS_SCRIPT_URL, json=payload)
    if response.status_code == 200:
        print("Successfully updated Google Sheet.")
    else:
        print("Failed to update Google Sheet.")

def send_notification_email():
    """Emails you when the process is done."""
    msg = EmailMessage()
    msg['Subject'] = "Your Daily Tech Job Scraper Update is Ready!"
    msg['From'] = EMAIL_SENDER
    msg['To'] = EMAIL_RECEIVER
    
    body = """Hello,

Your AI job scraper has finished checking all the company career pages.
Open your Google Sheet to view the updated list and apply for roles!

Happy hunting!
"""
    msg.set_content(body)

    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
        smtp.login(EMAIL_SENDER, EMAIL_PASSWORD)
        smtp.send_message(msg)

def main():
    all_company_jobs = {}
    for company, url in TARGET_COMPANIES.items():
        print(f"Processing {company}...")
        markdown = scrape_page(url)
        if markdown:
            jobs = extract_jobs_with_ai(markdown)
            if jobs: # Only add if jobs were found
                all_company_jobs[company] = jobs
            
    print("Sending data to Google Sheet Webhook...")
    update_google_sheet(all_company_jobs)
    
    print("Sending Notification Email...")
    send_notification_email()
    print("Complete!")

if __name__ == "__main__":
    main()
