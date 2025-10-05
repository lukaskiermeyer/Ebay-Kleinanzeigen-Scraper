import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import json
import threading
import requests
from bs4 import BeautifulSoup
import time
import statistics
import os  # Importiert für den Umgang mit Dateipfaden


# --- Hilfsfunktion für die Preisbereinigung ---
def clean_price(price_str):
    if not price_str or "zu verschenken" in price_str.lower():
        return None
    try:
        cleaned_str = price_str.replace("€", "").replace("VB", "").strip().replace(".", "").replace(",", ".")
        return float(cleaned_str)
    except (ValueError, TypeError):
        return None


# --- Regelbasierte Bewertungsfunktion ---
def evaluate_deals_with_rules(results):
    if not results: return []
    prices = [p for item in results if (p := clean_price(item.get('preis'))) is not None]
    if not prices:
        for item in results:
            item['evaluation'] = "Unbekannt"
            item['emoji'] = "❓"
        return results

    median_price = statistics.median(prices)
    good_deal_threshold = median_price * 0.8
    bad_deal_threshold = median_price * 1.5

    for item in results:
        price = clean_price(item.get('preis'))
        if price is None:
            item['evaluation'] = "Kein Preis"
            item['emoji'] = "❓"
        elif price <= good_deal_threshold:
            item['evaluation'] = "Guter Deal"
            item['emoji'] = "👍"
        elif price >= bad_deal_threshold:
            item['evaluation'] = "Teuer"
            item['emoji'] = "👎"
        else:
            item['evaluation'] = "Durchschnitt"
            item['emoji'] = "↔️"
    return results


# --- ANGEPASSTE WEB-SCRAPING-FUNKTION ---
def scrape_ebay_kleinanzeigen(search_term, min_price=None, max_price=None, max_pages=5):
    all_results = []
    base_url = "https://www.kleinanzeigen.de"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}

    for page_number in range(1, max_pages + 1):
        # URL für die Suchergebnisseite erstellen
        has_price_filter = min_price is not None or max_price is not None
        if has_price_filter:
            min_p = min_price if min_price is not None else ''
            max_p = max_price if max_price is not None else ''
            price_filter_segment = f"preis:{min_p}:{max_p}"
            search_url = f"{base_url}/s-{price_filter_segment}/seite:{page_number}/{search_term.replace(' ', '+')}/k0"
        else:
            search_url = f"{base_url}/s-seite:{page_number}/{search_term.replace(' ', '+')}/k0"

        try:
            # 1. Lade die Suchergebnisseite
            print(f"Lese Seite {page_number}...")
            response = requests.get(search_url, headers=headers)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')
            articles = soup.find_all('article', class_='aditem')
            if not articles: break

            # 2. Gehe durch jede Anzeige auf der Seite
            for article in articles:
                ad_link_tag = article.find('a', class_='ellipsis')
                if not ad_link_tag or not ad_link_tag.has_attr('href'):
                    continue

                ad_relative_url = ad_link_tag['href']
                ad_full_url = base_url + ad_relative_url

                try:
                    # 3. Rufe die einzelne Anzeigenseite auf
                    print(f"  -> Rufe Detailseite auf: {ad_full_url}")
                    ad_response = requests.get(ad_full_url, headers=headers)
                    ad_response.raise_for_status()
                    ad_soup = BeautifulSoup(ad_response.content, 'html.parser')

                    # 4. Extrahiere die VOLLSTÄNDIGEN Daten von der Detailseite
                    title = ad_soup.find('h1', id='viewad-title').get_text(strip=True) if ad_soup.find('h1',
                                                                                                       id='viewad-title') else 'N/A'
                    price = ad_soup.find('h2', id='viewad-price').get_text(strip=True) if ad_soup.find('h2',
                                                                                                       id='viewad-price') else 'N/A'
                    description = ad_soup.find('p', id='viewad-description-text').get_text(separator='\n',
                                                                                           strip=True) if ad_soup.find(
                        'p', id='viewad-description-text') else 'N/A'

                    all_results.append({
                        'titel': title,
                        'preis': price,
                        'beschreibung': description,
                        'url': ad_full_url
                    })
                    time.sleep(0.2)  # Kleine Pause zwischen den einzelnen Anzeigen
                except Exception as e:
                    print(f"    Fehler beim Abrufen der Detailseite: {e}")
                    continue  # Mache mit der nächsten Anzeige weiter

            time.sleep(0.5)  # Größere Pause zwischen den Ergebnisseiten
        except Exception as e:
            print(f"Fehler beim Laden der Ergebnisseite {page_number}: {e}")
            break

    return all_results


# --- Hauptanwendungsklasse für die GUI ---
class KleinanzeigenApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Kleinanzeigen Deal Finder")
        self.root.geometry("800x600")

        # ... (der restliche UI-Code bleibt gleich wie zuvor)
        style = ttk.Style()
        style.configure("TLabel", font=("Helvetica", 12))
        style.configure("TButton", font=("Helvetica", 12, "bold"))
        style.configure("TEntry", font=("Helvetica", 12))
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
        output_frame = ttk.Frame(root, padding="10")
        output_frame.pack(fill=tk.BOTH, expand=True)
        self.results_text = scrolledtext.ScrolledText(output_frame, wrap=tk.WORD, font=("Courier New", 11))
        self.results_text.pack(fill=tk.BOTH, expand=True)

    def start_search_thread(self):
        search_thread = threading.Thread(target=self.perform_search)
        search_thread.daemon = True
        search_thread.start()

    def perform_search(self):
        self.search_button.config(state=tk.DISABLED)
        self.results_text.delete(1.0, tk.END)
        self.results_text.insert(tk.END, "Suche läuft, dies kann einen Moment dauern...\n\n")
        self.root.update_idletasks()

        search_term = self.search_entry.get()
        min_price = self.min_price_entry.get() or None
        max_price = self.max_price_entry.get() or None

        if not search_term:
            self.results_text.insert(tk.END, "Fehler: Bitte gib einen Suchbegriff ein.")
            self.search_button.config(state=tk.NORMAL)
            return

        results = scrape_ebay_kleinanzeigen(search_term, min_price, max_price)
        evaluated_results = evaluate_deals_with_rules(results)

        self.results_text.delete(1.0, tk.END)
        self.search_button.config(state=tk.NORMAL)

        if not evaluated_results:
            self.results_text.insert(tk.END, f"Keine Ergebnisse für '{search_term}' gefunden.")
        else:
            self.display_results(evaluated_results)
            # NEU: Speichere die Ergebnisse als JSON-Datei
            self.save_results_to_json(evaluated_results, search_term)

    def display_results(self, results):
        self.results_text.insert(tk.END, f"--- {len(results)} Ergebnisse gefunden ---\n\n")
        for item in results:
            self.results_text.insert(tk.END, f"{item.get('emoji', '')} {item.get('evaluation', '')}\n")
            self.results_text.insert(tk.END, f"Titel: {item['titel']}\n")
            self.results_text.insert(tk.END, f"Preis: {item['preis']}\n")
            self.results_text.insert(tk.END, f"URL: {item['url']}\n")
            # Zeige nur einen Teil der Beschreibung in der UI an, um es übersichtlich zu halten
            description_preview = (item['beschreibung'][:200] + '...') if len(item['beschreibung']) > 200 else item[
                'beschreibung']
            self.results_text.insert(tk.END, f"Beschreibung: {description_preview}\n")
            self.results_text.insert(tk.END, "-" * 60 + "\n\n")

    # NEUE FUNKTION ZUM SPEICHERN
    def save_results_to_json(self, results, search_term):
        # Erstellt einen sicheren Dateinamen aus dem Suchbegriff
        filename = f"ergebnisse_{search_term.replace(' ', '_').lower()}.json"

        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(results, f, ensure_ascii=False, indent=4)

            # Zeige eine Erfolgsmeldung in der UI an
            full_path = os.path.abspath(filename)
            self.results_text.insert(tk.END,
                                     f"\n\n--- ERFOLG ---\nErgebnisse wurden erfolgreich gespeichert in:\n{full_path}\n")

            # Optional: Zeige eine Popup-Meldung
            # messagebox.showinfo("Erfolg", f"Ergebnisse wurden in {filename} gespeichert.")

        except Exception as e:
            messagebox.showerror("Fehler beim Speichern", f"Die Datei konnte nicht gespeichert werden.\nFehler: {e}")


# --- Hauptprogramm ---
if __name__ == "__main__":
    root = tk.Tk()
    app = KleinanzeigenApp(root)
    root.mainloop()