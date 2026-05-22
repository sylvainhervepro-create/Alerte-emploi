import feedparser
import smtplib
import os
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime, timedelta
from urllib.parse import quote

# ── Configuration ──────────────────────────────────────────────
GMAIL_USER     = os.environ["GMAIL_USER"]
GMAIL_PASSWORD = os.environ["GMAIL_PASSWORD"]
RECIPIENT      = "sylvainhervepro@gmail.com"

KEYWORDS = [
    "directeur général", "directeur general",
    "CEO", "COO", "CFO", "DAF",
    "directeur administratif", "directeur financier",
    "directeur marketing digital", "DG",
]

EXCLUDE = ["stage", "alternance", "apprentissage", "stagiaire"]

# ── Sources RSS ─────────────────────────────────────────────────
def build_feeds():
    base_kw = quote("directeur général OR CEO OR COO OR CFO Paris")
    return [
        # Indeed
        f"https://fr.indeed.com/rss?q=directeur+g%C3%A9n%C3%A9ral+CEO+COO+CFO&l=Paris&sort=date",
        # Cadremploi
        "https://www.cadremploi.fr/rss/offres?motsCles=directeur+general+CEO+COO+CFO&lieuCode=75&lieuLabel=Paris",
        # LinkedIn (flux RSS public par recherche)
        "https://www.linkedin.com/jobs/search/?keywords=directeur+g%C3%A9n%C3%A9ral+CEO+COO&location=Paris&f_TPR=r86400&format=rss",
    ]

# ── Filtrage ────────────────────────────────────────────────────
def is_relevant(entry):
    text = (entry.get("title","") + " " + entry.get("summary","")).lower()
    has_keyword = any(kw.lower() in text for kw in KEYWORDS)
    has_exclude = any(ex.lower() in text for ex in EXCLUDE)
    return has_keyword and not has_exclude

def fetch_jobs():
    jobs = []
    yesterday = datetime.now() - timedelta(days=1)
    for url in build_feeds():
        feed = feedparser.parse(url)
        for entry in feed.entries:
            # Filtre date (< 24h)
            published = entry.get("published_parsed")
            if published:
                pub_date = datetime(*published[:6])
                if pub_date < yesterday:
                    continue
            if is_relevant(entry):
                jobs.append({
                    "title":   entry.get("title", "Sans titre"),
                    "company": entry.get("author", entry.get("source", {}).get("title", "?")),
                    "link":    entry.get("link", "#"),
                    "summary": entry.get("summary", "")[:300],
                    "source":  feed.feed.get("title", "Job Board"),
                })
    return jobs

# ── Email HTML ──────────────────────────────────────────────────
def build_html(jobs):
    date_str = datetime.now().strftime("%A %d %B %Y")
    cards = ""
    for j in jobs:
        cards += f"""
        <div style="border:1px solid #e0e0e0;border-radius:8px;padding:16px;margin-bottom:16px;">
          <h3 style="margin:0 0 4px;color:#1a1a2e;">{j['title']}</h3>
          <p style="margin:0 0 8px;color:#555;font-size:13px;">
            {j['company']} &nbsp;|&nbsp; <em>{j['source']}</em>
          </p>
          <p style="margin:0 0 12px;font-size:13px;color:#333;">{j['summary']}…</p>
          <a href="{j['link']}" style="background:#2e7d32;color:white;padding:8px 16px;
             border-radius:4px;text-decoration:none;font-size:13px;">Voir l'offre →</a>
        </div>"""

    if not cards:
        cards = "<p style='color:#888;'>Aucune nouvelle offre correspondant à vos critères aujourd'hui.</p>"

    return f"""
    <html><body style="font-family:Arial,sans-serif;max-width:680px;margin:auto;padding:20px;">
      <h2 style="color:#2e7d32;">🎯 Offres d'emploi — {date_str}</h2>
      <p style="color:#555;">Profil : <strong>CEO / COO / CFO</strong> · Paris & IDF · 100K€+</p>
      <hr style="border:none;border-top:2px solid #2e7d32;margin:16px 0;">
      <p><strong>{len(jobs)} offre(s) trouvée(s)</strong></p>
      {cards}
      <hr style="border:none;border-top:1px solid #eee;margin-top:32px;">
      <p style="font-size:11px;color:#aaa;">Généré automatiquement · job-alert</p>
    </body></html>"""

# ── Envoi email ─────────────────────────────────────────────────
def send_email(jobs):
    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"[Job Alert] {len(jobs)} offre(s) · {datetime.now().strftime('%d/%m/%Y')}"
    msg["From"]    = GMAIL_USER
    msg["To"]      = RECIPIENT
    msg.attach(MIMEText(build_html(jobs), "html"))

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(GMAIL_USER, GMAIL_PASSWORD)
        server.sendmail(GMAIL_USER, RECIPIENT, msg.as_string())
    print(f"✅ Email envoyé avec {len(jobs)} offre(s)")

# ── Main ────────────────────────────────────────────────────────
if __name__ == "__main__":
    jobs = fetch_jobs()
    send_email(jobs)
