import feedparser
import smtplib
from email.mime.text import MIMEText
import google.generativeai as genai
import os

# 1. Configure the LLM
genai.configure(api_key=os.environ["GEMINI_API_KEY"])
model = genai.GenerativeModel("gemini-1.5-flash")

# 2. Define the exact extraction templates
inorganic_prompt = """
You are a battery materials expert. Analyze this abstract about an inorganic NMC811 lithium coin cell. 
Extract the following exact data points in a bulleted list. If a metric is missing, explicitly write "Not specified in abstract".
*   **Specific Capacity:** (e.g., mAh/g)
*   **Absolute Capacity:** (e.g., mAh)
*   **Material Percentages:** (e.g., 90% NMC811, 5% PVDF binder, 5% carbon black)
*   **Core Innovation:** (What is the novel methodology, coating, or electrolyte finding?)

Title: {title}
Abstract: {abstract}
"""

organic_prompt = """
You are a battery materials expert. Analyze this abstract about an organic cathode lithium coin cell. 
Extract the following exact data points in a bulleted list. If a metric is missing, explicitly write "Not specified in abstract".
*   **Specific Capacity:** (e.g., mAh/g)
*   **Absolute Capacity:** (e.g., mAh)
*   **Stability:** (e.g., capacity retention % over X cycles)
*   **Core Innovation:** (What is the novel molecule, e.g., triphenylamine derivatives, or structural design?)

Title: {title}
Abstract: {abstract}
"""

# 3. Fetch and process both feeds
summaries = ["<h2>Inorganic NMC811 Research</h2>"]

# Fetches the latest papers mentioning NMC811 and cathodes
inorganic_feed = feedparser.parse("http://export.arxiv.org/api/query?search_query=all:NMC811+AND+all:cathode&start=0&max_results=3&sortBy=submittedDate&sortOrder=descending")
for entry in inorganic_feed.entries:
    response = model.generate_content(inorganic_prompt.format(title=entry.title, abstract=entry.summary))
    summaries.append(f"<h3>{entry.title}</h3><a href='{entry.link}'>Paper Link</a><br>{response.text}")

summaries.append("<hr><h2>Organic Cathode Research</h2>")

# Fetches the latest papers mentioning organic lithium cathodes
organic_feed = feedparser.parse("http://export.arxiv.org/api/query?search_query=all:organic+AND+all:cathode+AND+all:lithium&start=0&max_results=3&sortBy=submittedDate&sortOrder=descending")
for entry in organic_feed.entries:
    response = model.generate_content(organic_prompt.format(title=entry.title, abstract=entry.summary))
    summaries.append(f"<h3>{entry.title}</h3><a href='{entry.link}'>Paper Link</a><br>{response.text}")

# 4. Format and send the email
html_content = "<br><br>".join(summaries)
msg = MIMEText(html_content, "html")
msg['Subject'] = "Daily Battery Research Summaries (Dual Track)"
msg['From'] = os.environ["SENDER_EMAIL"]
msg['To'] = os.environ["RECEIVER_EMAIL"]

with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
    server.login(os.environ["SENDER_EMAIL"], os.environ["EMAIL_APP_PASSWORD"])
    server.send_message(msg)
