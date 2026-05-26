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
        {"motsCles": "directeur général",         "typeContrat": "CDI"},
        {"motsCles": "CEO",                        "typeContrat": "CDI"},
        {"motsCles": "COO directeur opérations",   "typeContrat": "CDI"},
        {"motsCles": "CFO directeur financier",    "typeContrat": "CDI"},
        {"motsCles": "directeur marketing digital","typeContrat": "CDI"},
    ]
    common_params = {
        "departement": "75,92,93,94,78",  # Paris + petite couronne + Yvelines
        "minCreationDate": datetime.now().strftime("%Y-%m-%dT00:00:00Z"),
        "range":          "0-9",
        "sort":           "1",  # tri par date
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

# ── Email HTML ──────────────────────────────────────────────────
def build_html(jobs):
    date_str = datetime.now().strftime("%A %d %B %Y")
    cards = ""
    for j in jobs:
        cards += f"""
        <div style="border:1px solid #e0e0e0;border-radius:8px;padding:16px;margin-bottom:16px;">
          <h3 style="margin:0 0 4px;color:#1a1a2e;">{j['title']}</h3>
          <p style="margin:0 0 4px;color:#555;font-size:13px;">
            <strong>{j['company']}</strong> &nbsp;|&nbsp; 📍 {j['location']}
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
    send_email(jobs)
