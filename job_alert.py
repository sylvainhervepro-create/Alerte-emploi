import smtplib
import os
import requests
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime

# ── Configuration ──────────────────────────────────────────────
GMAIL_USER      = os.environ["GMAIL_USER"]
GMAIL_PASSWORD  = os.environ["GMAIL_PASSWORD"]
FT_CLIENT_ID    = os.environ["FT_CLIENT_ID"]
FT_CLIENT_SECRET= os.environ["FT_CLIENT_SECRET"]
RECIPIENT       = "sylvainhervepro@gmail.com"

# ── Authentification France Travail ─────────────────────────────
def get_ft_token():
    url = "https://entreprise.francetravail.fr/connexion/oauth2/access_token"
    params = {"realm": "/partenaire"}
    data = {
        "grant_type":    "client_credentials",
        "client_id":     FT_CLIENT_ID,
        "client_secret": FT_CLIENT_SECRET,
        "scope":         "api_offresdemploiv2 o2dsoffre",
    }
    r = requests.post(url, params=params, data=data)
    r.raise_for_status()
    return r.json()["access_token"]

# ── Récupération des offres ─────────────────────────────────────
def fetch_jobs(token):
    url = "https://api.francetravail.io/partenaire/offresdemploi/v2/offres/search"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept":        "application/json",
    }
    # Recherches multiples pour couvrir votre profil
    searches = [
        {"motsCles": "directeur général",          "typeContrat": "CDI"},
        {"motsCles": "directeur de filiale",        "typeContrat": "CDI"},
        {"motsCles": "directeur d activité",        "typeContrat": "CDI"},
        {"motsCles": "directeur de site",           "typeContrat": "CDI"},
        {"motsCles": "gérant dirigeant",            "typeContrat": "CDI"},
    ]
    today = datetime.now()
    common_params = {
        "departement":    "75,92,93,94,78",
        "minCreationDate": today.strftime("%Y-%m-%dT00:00:00Z"),
        "maxCreationDate": today.strftime("%Y-%m-%dT23:59:59Z"),
        "salaireMin":     "100000",
        "range":          "0-9",
        "sort":           "1",
    }
    jobs = []
    seen_ids = set()
    for search in searches:
        params = {**common_params, **search}
        r = requests.get(url, headers=headers, params=params)
        if r.status_code != 200:
            print(f"❌ Erreur {r.status_code} pour '{search['motsCles']}' : {r.text}")
            continue
        data = r.json()
        print(f"✅ '{search['motsCles']}' → {len(data.get('resultats', []))} résultat(s)")
        for offre in data.get("resultats", []):
            if offre["id"] in seen_ids:
                continue
            seen_ids.add(offre["id"])
            title = offre.get("intitule", "").lower()
            exclude_titles = ["infirmier", "infirmiere", "infirmière", "infirmièr",
                            "comptable", "assistant", "technicien", "commercial", 
                            "ingénieur", "développeur", "aide-soignant", "médecin"]
            include_titles = ["directeur", "director", "ceo", "coo", "cfo",
                            "daf", "général", "general", "président", "managing",
                            "gérant", "filiale", "activité", "site"]
            if not any(inc in title for inc in include_titles):
                continue
            if any(ex in title for ex in exclude_titles):
                continue
            jobs.append({
                "title":    offre.get("intitule", "Sans titre"),
                "company":  offre.get("entreprise", {}).get("nom", "Entreprise non précisée"),
                "location": offre.get("lieuTravail", {}).get("libelle", ""),
                "contract": offre.get("typeContratLibelle", ""),
                "salary":   offre.get("salaire", {}).get("libelle", "Non précisé"),
                "link":     offre.get("origineOffre", {}).get("urlOrigine",
                            f"https://candidat.francetravail.fr/offres/recherche/detail/{offre['id']}"),
                "description": offre.get("description", "")[:300],
            })
    return jobs
    
# ── Welcome to the Jungle : alerte email native recommandée ────
def fetch_jobs_wttj():
    return []

# ── Récupération des offres Indeed via RSS ──────────────────────
def fetch_jobs_indeed():
    import feedparser
    searches = [
        "directeur+général",
        "CEO+directeur",
        "COO+directeur+opérations",
        "CFO+directeur+financier",
        "directeur+filiale+PME",
    ]
    jobs = []
    seen_ids = set()
    for kw in searches:
        url = f"https://fr.indeed.com/rss?q={kw}&l=Île-de-France&sc=0kf%3Aattr%28DSQF7%29%3B&sort=date"
        try:
            feed = feedparser.parse(url)
            print(f"ℹ️ Indeed '{kw}' → {len(feed.entries)} entrée(s)")
            for entry in feed.entries:
                oid = entry.get("id", entry.get("link", ""))
                if oid in seen_ids:
                    continue
                seen_ids.add(oid)
                title = entry.get("title", "").lower()
                include_titles = ["directeur", "director", "ceo", "coo", "cfo",
                                "daf", "général", "general", "président", "managing",
                                "gérant", "filiale"]
                if not any(inc in title for inc in include_titles):
                    continue
                jobs.append({
                    "title":       entry.get("title", "Sans titre"),
                    "company":     entry.get("author", "?"),
                    "location":    "Île-de-France",
                    "contract":    "CDI",
                    "salary":      "Non précisé",
                    "link":        entry.get("link", "#"),
                    "description": entry.get("summary", "")[:300],
                    "source":      "Indeed",
                })
        except Exception as e:
            print(f"❌ Indeed erreur '{kw}' : {e}")
    print(f"✅ Indeed total → {len(jobs)} offre(s) pertinente(s)")
    return jobs    
    
# ── Email HTML ──────────────────────────────────────────────────
def build_html(jobs):
    date_str = datetime.now().strftime("%A %d %B %Y")
    cards = ""
    for j in jobs:
        cards += f"""
        <div style="border:1px solid #e0e0e0;border-radius:8px;padding:16px;margin-bottom:16px;">
          <h3 style="margin:0 0 4px;color:#1a1a2e;">{j['title']}</h3>
          <p style="margin:0 0 4px;color:#555;font-size:13px;">
            <strong>{j['company']}</strong> &nbsp;|&nbsp; 📍 {j['location']} &nbsp;|&nbsp; <em>{j.get('source','France Travail')}</em>
          </p>
          </p>
          <p style="margin:0 0 8px;color:#888;font-size:12px;">
            {j['contract']} &nbsp;·&nbsp; 💶 {j['salary']}
          </p>
          <p style="margin:0 0 12px;font-size:13px;color:#333;">{j['description']}…</p>
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
      <p style="font-size:11px;color:#aaa;">Généré automatiquement · job-alert · France Travail API</p>
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
    token = get_ft_token()
    print(f"✅ Token obtenu : {token[:10]}...")
    jobs  = fetch_jobs(token)
    jobs += fetch_jobs_wttj()
    jobs += fetch_jobs_indeed()     # ← ajouter cette ligne
    send_email(jobs)
