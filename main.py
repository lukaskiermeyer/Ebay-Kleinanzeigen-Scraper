import tkinter as tk
from tkinter import ttk, scrolledtext
import json
import threading  # Wichtig, damit die UI während des Scrapens nicht einfriert

# Importiere hier die Web-Scraping-Funktion aus dem vorherigen Skript.
# (Ich habe den Code der Einfachheit halber direkt hier eingefügt)
import requests
from bs4 import BeautifulSoup
import time


def scrape_ebay_kleinanzeigen(search_term, min_price=None, max_price=None, max_pages=5):
    """Die Web-Scraping-Funktion von vorhin."""
    search_term_formatted = search_term.replace(' ', '+')
    all_results = []
    base_url = "https://www.kleinanzeigen.de"

    for page_number in range(1, max_pages + 1):
        has_price_filter = min_price is not None or max_price is not None
        if has_price_filter:
            min_p = min_price if min_price is not None else ''
            max_p = max_price if max_price is not None else ''
            price_filter_segment = f"preis:{min_p}:{max_p}"
            url = f"{base_url}/s-{price_filter_segment}/seite:{page_number}/{search_term_formatted}/k0"
        else:
            url = f"{base_url}/s-seite:{page_number}/{search_term_formatted}/k0"

        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}

        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')
            articles = soup.find_all('article', class_='aditem')
            if not articles: break

            for article in articles:
                title_tag = article.find('a', class_='ellipsis')
                price_tag = article.find('p', class_='aditem-main--middle--price-shipping--price')
                description_tag = article.find('p', class_='aditem-main--middle--description')
                all_results.append({
                    'titel': title_tag.text.strip() if title_tag else 'N/A',
                    'preis': price_tag.text.strip() if price_tag else 'N/A',
                    'beschreibung': description_tag.text.strip() if description_tag else 'N/A'
                })
            time.sleep(0.5)
        except requests.exceptions.RequestException as e:
            print(f"Fehler: {e}")
            break

    return all_results


# --- Hauptanwendungsklasse für die GUI ---
class KleinanzeigenApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Kleinanzeigen Deal Finder")
        self.root.geometry("800x600")

        # Style-Konfiguration
        style = ttk.Style()
        style.configure("TLabel", font=("Helvetica", 12))
        style.configure("TButton", font=("Helvetica", 12, "bold"))
        style.configure("TEntry", font=("Helvetica", 12))

        # --- Eingabe-Frame ---
        input_frame = ttk.Frame(root, padding="10")
        input_frame.pack(fill=tk.X)

        ttk.Label(input_frame, text="Suchbegriff:").pack(side=tk.LEFT, padx=5)
        self.search_entry = ttk.Entry(input_frame, width=30)
        self.search_entry.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=5)

        ttk.Label(input_frame, text="Preis von:").pack(side=tk.LEFT, padx=5)
        self.min_price_entry = ttk.Entry(input_frame, width=8)
        self.min_price_entry.pack(side=tk.LEFT, padx=5)

        ttk.Label(input_frame, text="bis:").pack(side=tk.LEFT, padx=5)
        self.max_price_entry = ttk.Entry(input_frame, width=8)
        self.max_price_entry.pack(side=tk.LEFT, padx=5)

        self.search_button = ttk.Button(input_frame, text="Suchen", command=self.start_search_thread)
        self.search_button.pack(side=tk.LEFT, padx=10)

        # --- Ausgabe-Frame ---
        output_frame = ttk.Frame(root, padding="10")
        output_frame.pack(fill=tk.BOTH, expand=True)

        self.results_text = scrolledtext.ScrolledText(output_frame, wrap=tk.WORD, font=("Courier New", 11))
        self.results_text.pack(fill=tk.BOTH, expand=True)

    def start_search_thread(self):
        # Starte die Suche in einem separaten Thread, um die GUI nicht zu blockieren
        search_thread = threading.Thread(target=self.perform_search)
        search_thread.daemon = True  # Thread beendet sich, wenn das Hauptprogramm schließt
        search_thread.start()

    def perform_search(self):
        # Deaktiviere den Button und zeige eine Lade-Nachricht an
        self.search_button.config(state=tk.DISABLED)
        self.results_text.delete(1.0, tk.END)
        self.results_text.insert(tk.END, "Suche läuft, bitte warten...\n\n")
        self.root.update_idletasks()  # Aktualisiert die UI sofort

        # Lese die Eingaben aus den Feldern
        search_term = self.search_entry.get()
        min_price = self.min_price_entry.get() or None
        max_price = self.max_price_entry.get() or None

        if not search_term:
            self.results_text.insert(tk.END, "Fehler: Bitte gib einen Suchbegriff ein.")
            self.search_button.config(state=tk.NORMAL)
            return

        # Führe das Scraping durch
        results = scrape_ebay_kleinanzeigen(search_term, min_price, max_price)

        # Leere das Textfeld und aktiviere den Button wieder
        self.results_text.delete(1.0, tk.END)
        self.search_button.config(state=tk.NORMAL)

        # Zeige die Ergebnisse an
        if not results:
            self.results_text.insert(tk.END, f"Keine Ergebnisse für '{search_term}' gefunden.")
        else:
            self.display_results(results)

    def display_results(self, results):
        # Zeigt die JSON-Daten in einer ansprechenden, formatierten Weise an
        self.results_text.insert(tk.END, f"--- {len(results)} Ergebnisse gefunden ---\n\n")
        for item in results:
            self.results_text.insert(tk.END, f"Titel: {item['titel']}\n")
            self.results_text.insert(tk.END, f"Preis: {item['preis']}\n")
            self.results_text.insert(tk.END, f"Beschreibung: {item['beschreibung']}\n")
            self.results_text.insert(tk.END, "-" * 50 + "\n\n")


# --- Hauptprogramm ---
if __name__ == "__main__":
    root = tk.Tk()
    app = KleinanzeigenApp(root)
    root.mainloop()