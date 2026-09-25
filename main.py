import requests
import smtplib
from email.mime.text import MIMEText
import google.generativeai as genai
import os

# Configure the LLM
genai.configure(api_key=os.environ["GEMINI_API_KEY"])
model = genai.GenerativeModel("gemini-1.5-flash")

def rebuild_abstract(inverted_index):
    """OpenAlex compresses abstracts. This reconstructs them into readable text."""
    if not inverted_index: return "No abstract text available."
    max_idx = max([max(positions) for positions in inverted_index.values()])
    words = [""] * (max_idx + 1)
    for word, positions in inverted_index.items():
        for pos in positions:
            words[pos] = word
    return " ".join(words)

def get_top_paper(search_query):
    """Searches OpenAlex using the Polite Pool to guarantee we are not blocked."""
    url = "https://api.openalex.org/works"
    params = {
        "search": search_query,
        "filter": "publication_year:2022-2026,has_abstract:true",
        "per_page": 1,
        "mailto": os.environ["SENDER_EMAIL"] # CRITICAL: This bypasses the blocks
    }
    
    try:
        response = requests.get(url, params=params)
        if response.status_code != 200:
            return None, f"OpenAlex API Error: {response.status_code}"
            
        data = response.json()
        if data.get("results"):
            paper = data["results"][0]
            abstract = rebuild_abstract(paper.get("abstract_inverted_index"))
            return {
                "title": paper.get("title"),
                "url": paper.get("doi") or paper.get("id"),
                "year": paper.get("publication_year"),
                "venue": paper.get("primary_location", {}).get("source", {}).get("display_name", "Unknown Journal"),
                "abstract": abstract
            }, None
        return None, "Search succeeded, but no papers found."
    except Exception as e:
        return None, f"Script Error: {str(e)}"

# 1. Search OpenAlex
inorganic_paper, inorg_error = get_top_paper("NMC811 cathode coin cell gel polymer")
organic_paper, org_error = get_top_paper("triphenylamine cathode lithium coin cell")

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
    summaries.append(f"<b>Journal:</b> {inorganic_paper.get('venue')} ({inorganic_paper['year']})<br>")
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
    summaries.append(f"<b>Journal:</b> {organic_paper.get('venue')} ({organic_paper['year']})<br>")
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
