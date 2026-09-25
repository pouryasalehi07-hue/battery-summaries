import requests
import smtplib
from email.mime.text import MIMEText
import google.generativeai as genai
import os

# Configure the LLM
genai.configure(api_key=os.environ["GEMINI_API_KEY"])
model = genai.GenerativeModel("gemini-1.5-flash")

def get_top_paper(search_query):
    """Searches Semantic Scholar for the top relevant paper from 2022-2026 with an abstract."""
    url = "https://api.semanticscholar.org/graph/v1/paper/search"
    params = {
        "query": search_query,
        "year": "2022-2026",
        "fields": "title,url,abstract,venue,year",
        "limit": 15  # Increased limit to guarantee we find one with a valid abstract
    }
    
    response = requests.get(url, params=params).json()
    if "data" in response:
        for paper in response["data"]:
            if paper.get("abstract"): 
                return paper
    return None

# Broadened queries so the database actually returns results
inorganic_paper = get_top_paper("NMC811 cathode")
organic_paper = get_top_paper("triphenylamine cathode lithium")

summaries = ["<h2>Top Inorganic NMC811 Paper of the Week</h2>"]

if inorganic_paper:
    inorganic_prompt = f"""
    You are a battery materials expert. Analyze this abstract.
    Extract exactly:
    *   **Target Material:**
    *   **Specific Capacity:**
    *   **Absolute Capacity:**
    *   **Material Percentages:**
    *   **Core Innovation:** (Look for gel polymer electrolytes or coatings)

    Title: {inorganic_paper['title']}
    Abstract: {inorganic_paper['abstract']}
    """
    response = model.generate_content(inorganic_prompt)
    summaries.append(f"<h3>{inorganic_paper['title']}</h3>")
    summaries.append(f"<b>Journal:</b> {inorganic_paper.get('venue', 'Unknown Journal')} ({inorganic_paper['year']})<br>")
    summaries.append(f"<a href='{inorganic_paper['url']}'>Link to Paper</a><br>{response.text}")
else:
    summaries.append("<p>No highly relevant inorganic papers with abstracts found for this timeframe.</p>")

summaries.append("<hr><h2>Top Organic Cathode Paper of the Week</h2>")

if organic_paper:
    organic_prompt = f"""
    You are a battery materials expert. Analyze this abstract.
    Extract exactly:
    *   **Specific Capacity:**
    *   **Absolute Capacity:**
    *   **Stability:**
    *   **Core Innovation:** (Focus on the molecular design or stability improvements)

    Title: {organic_paper['title']}
    Abstract: {organic_paper['abstract']}
    """
    response = model.generate_content(organic_prompt)
    summaries.append(f"<h3>{organic_paper['title']}</h3>")
    summaries.append(f"<b>Journal:</b> {organic_paper.get('venue', 'Unknown Journal')} ({organic_paper['year']})<br>")
    summaries.append(f"<a href='{organic_paper['url']}'>Link to Paper</a><br>{response.text}")
else:
    summaries.append("<p>No highly relevant organic papers with abstracts found for this timeframe.</p>")

# Format and send the email
html_content = "<br><br>".join(summaries)
msg = MIMEText(html_content, "html")
msg['Subject'] = "Weekly Battery Research Deep Dive"
msg['From'] = os.environ["SENDER_EMAIL"]
msg['To'] = os.environ["RECEIVER_EMAIL"]

with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
    server.login(os.environ["SENDER_EMAIL"], os.environ["EMAIL_APP_PASSWORD"])
    server.send_message(msg)
