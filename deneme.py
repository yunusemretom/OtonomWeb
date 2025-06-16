import requests
from bs4 import BeautifulSoup
import time
import json
from typing import Dict, List, Any, Optional
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException

class VisasBotScraper:
    def __init__(self, headless: bool = True):
        """
        Visasbot.com scraper sınıfı
        
        Args:
            headless (bool): Tarayıcıyı görünmez modda çalıştır
        """
        self.headless = headless
        self.driver = None
        
    def setup_driver(self):
        """Selenium WebDriver'ı kurulum"""
        chrome_options = Options()
        if self.headless:
            chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
        
        self.driver = webdriver.Chrome(options=chrome_options)
        
    def close_driver(self):
        """WebDriver'ı kapat"""
        if self.driver:
            self.driver.quit()
            
    def scrape_visa_cards(self, url: str, wait_time: int = 10) -> List[Dict[str, Any]]:
        """
        Visasbot.com'dan visa kartlarını çeker
        
        Args:
            url (str): Scrape edilecek URL
            wait_time (int): Sayfa yüklenmesi için bekleme süresi
            
        Returns:
            List[Dict[str, Any]]: Visa kartları listesi
        """
        try:
            self.setup_driver()
            print(f"Sayfa yükleniyor: {url}")
            
            # Sayfayı yükle
            self.driver.get(url)
            
            # Sayfanın yüklenmesini bekle
            wait = WebDriverWait(self.driver, wait_time)
            
            # Visa kartlarının yüklenmesini bekle
            try:
                wait.until(EC.presence_of_element_located((By.CLASS_NAME, "visa-card-container")))
                print("Visa kartları yüklendi")
            except TimeoutException:
                print("Visa kartları yüklenemedi, sayfa kaynağını kontrol ediliyor...")
            
            # Biraz daha bekle (JavaScript yüklenmesi için)
            time.sleep(3)
            
            # Sayfa kaynağını al
            page_source = self.driver.page_source
            
            # BeautifulSoup ile parse et
            soup = BeautifulSoup(page_source, 'html.parser')
            
            # Visa kartlarını bul
            visa_cards = soup.find_all('div', class_='visa-card-container')
            print(f"Bulunan visa kartı sayısı: {len(visa_cards)}")
            
            # Her kartı parse et
            all_visa_info = []
            for i, card in enumerate(visa_cards):
                try:
                    visa_info = self.parse_single_visa_card(card, i+1)
                    all_visa_info.append(visa_info)
                    print(f"Kart {i+1} parse edildi: {visa_info.get('country_mission', {}).get('text', 'N/A')}")
                except Exception as e:
                    print(f"Kart {i+1} parse edilirken hata: {e}")
                    continue
            
            return all_visa_info
            
        except Exception as e:
            print(f"Scraping hatası: {e}")
            return []
        finally:
            self.close_driver()
    
    def parse_single_visa_card(self, card_element, card_number: int) -> Dict[str, Any]:
        """
        Tek bir visa kartını parse eder
        
        Args:
            card_element: BeautifulSoup element
            card_number (int): Kart numarası
            
        Returns:
            Dict[str, Any]: Parse edilmiş visa bilgileri
        """
        visa_info = {
            'card_number': card_number,
            'container_classes': card_element.get('class', []),
            'border_style': 'green' if 'border-green' in card_element.get('class', []) else 'default',
            
            # Tracking bilgileri
            'tracking': {
                'count': self._get_text_safe(card_element, '.tracking-count span'),
                'title': self._get_attribute_safe(card_element, '.tracking-count', 'title')
            },
            
            # Share button bilgileri
            'share_button': {
                'visa_id': self._get_attribute_safe(card_element, '.share-btn', 'data-visa-id'),
                'title': self._get_attribute_safe(card_element, '.share-btn', 'title')
            },
            
            # Status bilgileri
            'status': {
                'text': self._get_text_safe(card_element, '.status-text'),
                'last_checked': self._get_text_safe(card_element, '.last-checked', clean_text=True),
                'last_checked_title': self._get_attribute_safe(card_element, '.last-checked', 'title')
            },
            
            # Ülke ve misyon bilgileri
            'country_mission': self._parse_country_mission(card_element),
            
            # Visa detayları
            'details': self._parse_visa_details(card_element),
            
            # Action buttons
            'actions': self._parse_action_buttons(card_element)
        }
        
        return visa_info
    
    def _get_text_safe(self, element, selector: str, clean_text: bool = False) -> str:
        """Güvenli şekilde text içeriği alır"""
        found = element.select_one(selector)
        if found:
            text = found.get_text(strip=True)
            if clean_text and text.startswith('•'):
                text = text.replace('• ', '').strip()
            return text
        return ''
    
    def _get_attribute_safe(self, element, selector: str, attribute: str) -> str:
        """Güvenli şekilde attribute değeri alır"""
        found = element.select_one(selector)
        return found.get(attribute, '') if found else ''
    
    def _parse_country_mission(self, element) -> Dict[str, str]:
        """Ülke ve misyon bilgilerini parse eder"""
        country_element = element.select_one('.country-mission-row')
        
        if not country_element:
            return {'text': '', 'title': '', 'from': '', 'to': ''}
        
        text = country_element.get_text(strip=True)
        title = country_element.get('title', '')
        
        # "Turkey → France" formatını parse et
        parts = text.split(' → ') if ' → ' in text else text.split(' -> ')
        from_country = parts[0].strip() if len(parts) > 0 else ''
        to_country = parts[1].strip() if len(parts) > 1 else ''
        
        return {
            'text': text,
            'title': title,
            'from': from_country,
            'to': to_country
        }
    
    def _parse_visa_details(self, element) -> Dict[str, str]:
        """Visa detaylarını parse eder"""
        details = {}
        detail_lines = element.select('.visa-details .line')
        
        for line in detail_lines:
            text = line.get_text(strip=True)
            if ':' in text:
                key, value = text.split(':', 1)
                # Key'i temizle
                key = key.replace('<strong>', '').replace('</strong>', '').strip()
                details[key.lower().replace(' ', '_')] = value.strip()
        
        return details
    
    def _parse_action_buttons(self, element) -> Dict[str, Dict[str, str]]:
        """Action buttonlarını parse eder"""
        actions = {}
        
        # Book Now button
        book_now = element.select_one('.button-primary')
        if book_now:
            actions['book_now'] = {
                'href': book_now.get('href', ''),
                'target': book_now.get('target', ''),
                'title': book_now.get('title', ''),
                'text': book_now.get_text(strip=True)
            }
        
        # Track Now button
        track_now = element.select_one('.track-now-btn')
        if track_now:
            actions['track_now'] = {
                'visa_id': track_now.get('data-visa-id', ''),
                'title': track_now.get('title', ''),
                'disabled': track_now.has_attr('disabled'),
                'text': track_now.get_text(strip=True)
            }
        
        return actions
    
    def save_to_json(self, data: List[Dict[str, Any]], filename: str = 'visa_cards.json'):
        """Veriyi JSON dosyasına kaydet"""
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"Veriler {filename} dosyasına kaydedildi")
    
    def print_summary(self, visa_data: List[Dict[str, Any]]):
        """Visa kartlarının özetini yazdır"""
        if not visa_data:
            print("\nBelirtilen kriterlere uygun visa kartı bulunamadı.")
            return
            
        print("\nBulunan Visa Kartları:")
        print("="*50)
        
        for card in visa_data:
            print(f"\n--- Kart {card['card_number']} ---")
            print(f"Rota: {card['country_mission']['text']}")
            print(f"Durum: {card['status']['text']}")
            
            if 'details' in card:
                if 'type' in card['details']:
                    print(f"Tip: {card['details']['type']}")
                if 'category' in card['details']:
                    print(f"Kategori: {card['details']['category']}")
                if 'processing_time' in card['details']:
                    print(f"İşlem Süresi: {card['details']['processing_time']}")
                if 'validity' in card['details']:
                    print(f"Geçerlilik: {card['details']['validity']}")
            
            if 'book_now' in card['actions']:
                print(f"Rezervasyon: {card['actions']['book_now']['href']}")
            print("-"*30)

    def filter_visa_cards(self, visa_data: List[Dict[str, Any]], 
                         status: str = "open",
                         location: str = "Istanbul Beyoglu",
                         category: str = "Short Term / Kisa Donem / Court Sejour",
                         visa_type: str = "Short Term Standard") -> List[Dict[str, Any]]:
        """
        Visa kartlarını belirli kriterlere göre filtreler
        
        Args:
            visa_data: Filtrelenecek visa kartları listesi
            status: Aranacak durum (örn: "open")
            location: Aranacak konum (örn: "Istanbul Beyoglu")
            category: Aranacak kategori
            visa_type: Aranacak vize tipi
            
        Returns:
            List[Dict[str, Any]]: Filtrelenmiş visa kartları listesi
        """
        filtered_cards = []
        
        for card in visa_data:
            # Durum kontrolü - büyük/küçük harf duyarsız
            if card['status']['text'].lower() != status.lower():
                continue
                
            # Konum kontrolü - kısmi eşleşme
            if location.lower() not in card['country_mission']['text'].lower():
                continue
                
            # Kategori kontrolü - kısmi eşleşme
            if 'details' in card and 'category' in card['details']:
                if category.lower() not in card['details']['category'].lower():
                    continue
            
            # Vize tipi kontrolü - kısmi eşleşme
            if 'details' in card and 'type' in card['details']:
                if visa_type.lower() not in card['details']['type'].lower():
                    continue
                    
            filtered_cards.append(card)
            
        return filtered_cards

# Kullanım örneği
def main():
    url = "https://www.visasbot.com/#origin=tur&dest=fra"
    
    scraper = VisasBotScraper(headless=False)  # Tarayıcıyı görmek için False
    
    try:
        print("Visa kartları çekiliyor...")
        visa_cards = scraper.scrape_visa_cards(url, wait_time=15)
        
        if visa_cards:
            # Filtreleme kriterleri
            status = "closed"  # Büyük/küçük harf duyarsız olacak
            location = "Turkey → France"  # Tam rota
            category = "Short Term"  # Tam kategori
            visa_type = "Short Term Standard"  # Tam tip
            
            # Kartları filtrele
            filtered_cards = scraper.filter_visa_cards(visa_cards, status, location, category, visa_type)
            
            # Özet yazdır
            scraper.print_summary(filtered_cards)
            
            # JSON'a kaydet
            if filtered_cards:
                scraper.save_to_json(filtered_cards, 'filtered_visa_cards.json')
            else:
                print("\nFiltreleme kriterlerine uygun kart bulunamadı.")
                print("Mevcut kartlar:")
                scraper.print_summary(visa_cards)
        else:
            print("Hiç visa kartı bulunamadı.")
            
    except Exception as e:
        print(f"Ana hata: {e}")

if __name__ == "__main__":
    main()