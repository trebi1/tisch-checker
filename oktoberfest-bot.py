import os
import requests
from playwright.sync_api import sync_playwright
import sys

# --- KONFIGURATION ---
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
STATUS_FILE = "wiesn_status_3okt.txt"
TARGET_DATE = "03.10.2026"

ZELTE = [
    {"name": "Hacker-Pschorr", "url": "https://reservierung.derhimmelderbayern.de/reservierung"},
    {"name": "Hofbräu", "url": "https://reservierung.hb-festzelt.de/reservierung"},
    {"name": "Bräurosl", "url": "https://reservierung.braeurosl.de/reservation"},
    {"name": "Ochsenbraterei", "url": "https://reservierung.ochsenbraterei.de/reservierungen"},
    {"name": "Schottenhamel", "url": "https://reservierung.festhalle-schottenhamel.de/reservation/"}
]

def send_telegram(message):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print("Telegram-Konfiguration fehlt!")
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    try:
        # Timeout hinzugefügt, damit das Skript nicht hängen bleibt
        requests.post(url, json={"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "Markdown"}, timeout=10)
    except Exception as e:
        print(f"Telegram-Fehler: {e}")

def get_last_status():
    if os.path.exists(STATUS_FILE):
        with open(STATUS_FILE, "r", encoding="utf-8") as f:
            return set(f.read().splitlines())
    return set()

def save_status(status_set):
    with open(STATUS_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(status_set))

def check_wiesn():
    last_status = get_last_status()
    current_status = set()
    alerts = []

    with sync_playwright() as p:
        # Wichtig für GitHub Actions: --no-sandbox
        browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
        # Wir tarnen uns als normaler Desktop-Browser
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        )
        page = context.new_page()

        for zelt in ZELTE:
            try:
                print(f"Prüfe {zelt['name']}...")
                # Erhöhtes Timeout auf 45s, falls die Wiesn-Server langsam sind
                page.goto(zelt["url"], wait_until="networkidle", timeout=45000)
                
                # Wir geben der Seite Zeit, den Kalender zu rendern
                page.wait_for_timeout(2000)
                
                content = page.content()

                # Wir prüfen, ob das Datum im Text vorkommt
                if TARGET_DATE in content:
                    # Zusätzliche Prüfung: Ist es NICHT als "ausgebucht" oder "disabled" markiert?
                    # (Sehr einfach gehalten, um Fehlalarme zu vermeiden)
                    if "ausgebucht" not in content.lower():
                        current_status.add(zelt["name"])
                        if zelt["name"] not in last_status:
                            alerts.append(f"🥨 *{zelt['name']}*\nDatum {TARGET_DATE} im Kalender gefunden!\n🔗 [Hier klicken]({zelt['url']})")
                
            except Exception as e:
                print(f"Fehler bei {zelt['name']}: {str(e)[:100]}...") # Logge nur den Anfang des Fehlers

        browser.close()

    if alerts:
        send_telegram(f"🚨 *WIESN-TARGET GEFUNDEN!*\n\n" + "\n\n".join(alerts))
    
    # Speichere den Status immer (auch wenn leer), damit Git keine Probleme macht
    save_status(current_status)

if __name__ == "__main__":
    send_telegram("🤖 Test: Der Bot ist online und bereit!") # Diese Zeile einfügen
    try:
        check_wiesn()
    except Exception as global_e:
        print(f"Kritischer Fehler: {global_e}")
        sys.exit(1) # Beendet mit Fehler für GitHub Logs
