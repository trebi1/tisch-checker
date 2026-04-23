import os
import requests
from playwright.sync_api import sync_playwright

# 1. KONFIGURATION
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
STATUS_FILE = "wiesn_status_3okt.txt"

TARGET_DATE = "03.10.2026"
TARGET_DATE_ALT = "03.10.26"

ZELTE = [
    {"name": "Hacker-Pschorr", "url": "https://reservierung.derhimmelderbayern.de/reservierung"},
    {"name": "Hofbräu", "url": "https://reservierung.hb-festzelt.de/reservierung"},
    {"name": "Bräurosl", "url": "https://reservierung.braeurosl.de/reservation"},
    {"name": "Ochsenbraterei", "url": "https://reservierung.ochsenbraterei.de/reservierungen"},
    {"name": "Schottenhamel", "url": "https://reservierung.festhalle-schottenhamel.de/reservation/"}
]

def send_telegram(message):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print("Config fehlt")
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    requests.post(url, json={"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "Markdown"})

def get_last_status():
    if os.path.exists(STATUS_FILE):
        with open(STATUS_FILE, "r") as f:
            return set(f.read().splitlines())
    return set()

def save_status(status_set):
    with open(STATUS_FILE, "w") as f:
        f.write("\n".join(status_set))

def check_wiesn():
    last_status = get_last_status()
    current_status = set()
    alerts = []

    print(f"Starte echten Browser-Check für den {TARGET_DATE}...")

    # Playwright starten
    with sync_playwright() as p:
        # Einen unsichtbaren Chromium-Browser starten
        browser = p.chromium.launch(headless=True)
        # Tab öffnen und tarnen
        page = browser.new_page(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        )

        for zelt in ZELTE:
            try:
                print(f"Lade {zelt['name']}...")
                # Gehe zur URL und warte, bis im Netzwerk für 0,5 Sekunden nichts mehr passiert (alles ist geladen)
                page.goto(zelt["url"], timeout=30000, wait_until="networkidle")
                
                # Jetzt holen wir uns den finalen HTML-Code
                html = page.content()

                if TARGET_DATE in html or TARGET_DATE_ALT in html:
                    # Einfacher Check: Ist das Datum nicht direkt als 'disabled' oder 'ausgebucht' markiert?
                    if 'ausgebucht' not in html.lower() and 'disabled' not in html.lower():
                        current_status.add(zelt["name"])
                        if zelt["name"] not in last_status:
                            alerts.append(f"🍻 *{zelt['name']}*\nDatum {TARGET_DATE} im geladenen Kalender gefunden!\n🔗 [Hier klicken]({zelt['url']})")
                
            except Exception as e:
                print(f"Fehler bei {zelt['name']}: {e}")

        # Browser schließen, um Ressourcen freizugeben
        browser.close()

    if alerts:
        send_telegram(f"🎯 *WIESN-TARGET GEFUNDEN!*\nFür den {TARGET_DATE} scheint sich was zu tun:\n\n" + "\n\n".join(alerts))
    
    save_status(current_status)

if __name__ == "__main__":
    check_wiesn()
