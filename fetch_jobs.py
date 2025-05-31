import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from email.message import EmailMessage
from smtplib import SMTP_SSL
from dotenv import load_dotenv
import time
import json
import os

# Load environment variables
load_dotenv()

# Config
SEEN_JOBS_FILE = "seen_jobs.json"
URL = "https://www.bayt.com/en/uae/jobs/full-stack-developer-jobs/?filters%5Bjb_last_modification_date_interval%5D%5B%5D=3"
FETCH_INTERVAL = 1800
HEADLESS = False

# Email Config
EMAIL_ENABLED = True
SENDER_EMAIL = os.getenv("EMAIL")
EMAIL_PASSWORD = os.getenv("PASSWORD")
SMTP_SERVER = "mail.privateemail.com"
SMTP_PORT = int(os.getenv("PORT", 465))
HTML_TEMPLATE_FILE = "template.html"
CV_FILE_PATH = "./cv.pdf"

def load_seen_jobs():
    if os.path.exists(SEEN_JOBS_FILE):
        with open(SEEN_JOBS_FILE, "r") as f:
            return set(json.load(f))
    return set()

def save_seen_jobs(seen_jobs):
    with open(SEEN_JOBS_FILE, "w") as f:
        json.dump(list(seen_jobs), f)

def send_email(subject, body_html, attachment_path=None):
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = SENDER_EMAIL
    msg["To"] = SENDER_EMAIL
    msg.set_content("This is an HTML email with your job notification.")
    msg.add_alternative(body_html, subtype="html")

    if attachment_path and os.path.exists(attachment_path):
        with open(attachment_path, "rb") as f:
            msg.add_attachment(f.read(), maintype="application", subtype="pdf", filename="cv.pdf")

    try:
        with SMTP_SSL(SMTP_SERVER, SMTP_PORT) as smtp:
            smtp.login(SENDER_EMAIL, EMAIL_PASSWORD)
            smtp.send_message(msg)
        print("📧 Email sent.")
    except Exception as e:
        print("❌ Failed to send email:", e)

def prepare_and_send_email(job_title, job_link):
    if not EMAIL_ENABLED:
        return

    try:
        with open(HTML_TEMPLATE_FILE, "r", encoding="utf-8") as f:
            html_body = f.read().replace("{{JOB_TITLE}}", job_title).replace("{{JOB_LINK}}", job_link)
        send_email(f"🆕 New Job: {job_title}", html_body, CV_FILE_PATH)
    except Exception as e:
        print("⚠️ Error preparing email:", e)

def fetch_jobs():
    print("🚀 Launching undetected Chrome...")
    options = uc.ChromeOptions()
    if HEADLESS:
        options.add_argument("--headless")
    driver = uc.Chrome(options=options)

    try:
        driver.get(URL)
        WebDriverWait(driver, 15).until(
            EC.presence_of_all_elements_located((By.CSS_SELECTOR, 'li[data-job-id] h2 > a'))
        )

        seen_jobs = load_seen_jobs()
        new_jobs = []

        job_links = driver.find_elements(By.CSS_SELECTOR, 'li[data-job-id] h2 > a')
        print(f"🔍 Found {len(job_links)} job listings.")

        for job in job_links:
            title = job.text.strip()
            link = job.get_attribute("href")
            job_id = link.strip("/").split("/")[-1]

            if job_id not in seen_jobs:
                print("🆕 New Job Found:")
                print("🔗", title)
                print("🌐", link)
                new_jobs.append(job_id)

                # Send email
                prepare_and_send_email(title, link)

        if new_jobs:
            seen_jobs.update(new_jobs)
            save_seen_jobs(seen_jobs)
            print(f"✅ Saved {len(new_jobs)} new job(s).")
        else:
            print("🟢 No new jobs found.")

    except Exception as e:
        print("❌ Error during scraping:", e)
    finally:
        driver.quit()

def main():
    while True:
        print("\n🔄 Fetching jobs...")
        fetch_jobs()
        print(f"⏳ Waiting {FETCH_INTERVAL // 60} minutes...\n")
        time.sleep(FETCH_INTERVAL)

if __name__ == "__main__":
    main()
