import requests
import smtplib
from email.mime.text import MIMEText
import google.generativeai as genai
import os
import time

# Configure the LLM
genai.configure(api_key=os.environ["GEMINI_API_KEY"])
model = genai.GenerativeModel("gemini-1.5-flash")

def get_top_paper(search_query):
    """Searches Semantic Scholar with a built-in delay to bypass 429 rate limits."""
    url = "https://api.semanticscholar.org/graph/v1/paper/search"
    params = {
        "query": search_query,
        "year": "2022-2026",
        "fields": "title,url,abstract,venue,year",
        "limit": 15 
    }
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    # Try up to 3 times if we get blocked
    for attempt in range(3):
        try:
            response = requests.get(url, params=params, headers=headers)
            
            # If we hit the 429 limit, wait 5 seconds and try again
            if response.status_code == 429:
                time.sleep(5)
                continue
                
            if response.status_code != 200:
                return None, f"API Error {response.status_code}: {response.text}"
            
            data = response.json()
            if "data" in data:
                for paper in data["data"]:
                    if paper.get("abstract"): 
                        return paper, None
            return None, "Search succeeded, but no abstracts were found."
        except Exception as e:
            return None, f"Python Script Error: {str(e)}"
            
    return None, "Failed: API Blocked (Error 429) even after 3 delays."

# 1. Search Inorganic
inorganic_paper, inorg_error = get_top_paper("NMC811 cathode")

# 2. CRITICAL FIX: Pause the script for 5 seconds before the next search
time.sleep(5)

# 3. Search Organic
organic_paper, org_error = get_top_paper("triphenylamine cathode")

summaries = ["<h2>Top Inorganic NMC811 Paper of the Week</h2>"]

if inorganic_paper:
    inorganic_prompt = f"""
    You are a battery materials expert. Analyze this abstract.
    Extract exactly:
    *   **Target Material:**
    *   **Specific Capacity:**
    *   **Absolute Capacity:**
    *   **Material Percentages:**
    *   **Core Innovation:** 

    Title: {inorganic_paper['title']}
    Abstract: {inorganic_paper['abstract']}
    """
    response = model.generate_content(inorganic_prompt)
    summaries.append(f"<h3>{inorganic_paper['title']}</h3>")
    summaries.append(f"<b>Journal:</b> {inorganic_paper.get('venue', 'Unknown Journal')} ({inorganic_paper['year']})<br>")
    summaries.append(f"<a href='{inorganic_paper['url']}'>Link to Paper</a><br>{response.text}")
else:
    summaries.append(f"<p style='color:red;'><i>Failed: {inorg_error}</i></p>")

summaries.append("<hr><h2>Top Organic Cathode Paper of the Week</h2>")

if organic_paper:
    organic_prompt = f"""
    You are a battery materials expert. Analyze this abstract.
    Extract exactly:
    *   **Specific Capacity:**
    *   **Absolute Capacity:**
    *   **Stability:**
    *   **Core Innovation:**

    Title: {organic_paper['title']}
    Abstract: {organic_paper['abstract']}
    """
    response = model.generate_content(organic_prompt)
    summaries.append(f"<h3>{organic_paper['title']}</h3>")
    summaries.append(f"<b>Journal:</b> {organic_paper.get('venue', 'Unknown Journal')} ({organic_paper['year']})<br>")
    summaries.append(f"<a href='{organic_paper['url']}'>Link to Paper</a><br>{response.text}")
else:
    summaries.append(f"<p style='color:red;'><i>Failed: {org_error}</i></p>")

# Format and send the email
html_content = "<br><br>".join(summaries)
msg = MIMEText(html_content, "html")
msg['Subject'] = "Weekly Battery Research Deep Dive"
msg['From'] = os.environ["SENDER_EMAIL"]
msg['To'] = os.environ["RECEIVER_EMAIL"]

with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
    server.login(os.environ["SENDER_EMAIL"], os.environ["EMAIL_APP_PASSWORD"])
    server.send_message(msg)
