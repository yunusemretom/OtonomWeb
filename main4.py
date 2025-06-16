import sys
import time
import logging
import json
import re
import winsound
from datetime import datetime
from typing import Optional, Dict, Any
from dataclasses import dataclass, asdict
from enum import Enum
from bs4 import BeautifulSoup

import undetected_chromedriver as uc
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import pyautogui
from selenium.webdriver.common.action_chains import ActionChains

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, QWidget,
    QLabel, QLineEdit, QPushButton, QTextEdit, QGroupBox, QFormLayout,
    QComboBox, QProgressBar, QMessageBox, QInputDialog, QTabWidget,
    QScrollArea, QFrame, QSplitter
)
from PySide6.QtCore import QThread, Signal, Qt, QTimer
from PySide6.QtGui import QFont, QPalette, QColor, QPixmap, QIcon


class BookingStatus(Enum):
    IDLE = "Beklemede"
    LOGGING_IN = "Giriş yapılıyor"
    IN_QUEUE = "Sanal kuyrukta bekliyor"
    FINDING_APPOINTMENT = "Randevu aranıyor"
    FILLING_FORM = "Form dolduruluyor"
    COMPLETED = "Tamamlandı"
    ERROR = "Hata"


@dataclass 
class UserInfo:
    email: str = ""
    password: str = ""
    first_name: str = ""
    last_name: str = ""
    gender: str = "Male"
    birth_date: str = ""
    nationality: str = "Türkiye"
    passport_number: str = ""
    passport_expiry: str = ""
    reference_number: str = ""
    # Visa search settings
    visa_status: str = "closed"  # Büyük/küçük harf duyarsız
    visa_location: str = "Turkey → France"  # Tam rota
    visa_category: str = "Short Term"  # Kategori
    visa_type: str = "Short Term Standard"  # Tip
    check_interval: int = 30  # seconds
    wait_time: int = 180  # seconds
    check_visa_switch: str = "Evet"  # Whether to check visa availability from website

    @classmethod
    def load_from_file(cls):
        """Kaydedilmiş bilgileri JSON dosyasından yükle"""
        import json
        import os
        
        file_path = "user_info.json"
        
        if os.path.exists(file_path):
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                return cls(**data)
            except Exception as e:
                print(f"Bilgiler yüklenirken hata: {e}")
                return cls()
        return cls()

    def save_to_file(self) -> bool:
        """Kullanıcı bilgilerini JSON dosyasına kaydet"""
        import json
        
        try:
            data = {
                "email": self.email,
                "password": self.password, 
                "first_name": self.first_name,
                "last_name": self.last_name,
                "gender": self.gender,
                "birth_date": self.birth_date,
                "nationality": self.nationality,
                "passport_number": self.passport_number,
                "passport_expiry": self.passport_expiry,
                "reference_number": self.reference_number,
                # Visa search settings
                "visa_status": self.visa_status,
                "visa_location": self.visa_location,
                "visa_category": self.visa_category,
                "visa_type": self.visa_type,
                "check_interval": self.check_interval,
                "wait_time": self.wait_time,
                "check_visa_switch": self.check_visa_switch
            }
            
            with open("user_info.json", "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
            return True
            
        except Exception as e:
            print(f"Bilgiler kaydedilirken hata: {e}")
            return False

    def format_date(self, date_str: str) -> str:
        """Tarihi DDMMYYYY formatına dönüştür"""
        # Sadece rakamları al
        nums = ''.join(filter(str.isdigit, date_str))
        if len(nums) == 8:
            return nums
        return date_str


class VisaBookingWorker(QThread):
    status_changed = Signal(str)
    progress_changed = Signal(int)
    log_message = Signal(str)
    input_required = Signal(str, str)
    input_received = Signal(str)
    error_occurred = Signal(str)
    booking_completed = Signal()

    def __init__(self, user_info: UserInfo):
        super().__init__()
        self.user_info = user_info
        self.driver: Optional[webdriver.Chrome] = None
        self.wait: Optional[WebDriverWait] = None
        self.is_running = True
        self.user_input = ""
        self.input_event = None
        self.wait_time = 180  # Default wait time

    def check_visa_availability(self) -> bool:
        """Check if visa appointments are available"""
        try:
            self.log_message.emit("Vize randevu durumu kontrol ediliyor...")
            self.status_changed.emit("Randevu durumu kontrol ediliyor")
            
            # Visasbot.com'dan kontrol et
            url = "https://www.visasbot.com/#origin=tur&dest=fra"
            self.driver.get(url)
            time.sleep(5)  # Sayfanın yüklenmesi için bekle
            
            # Visa kartlarının yüklenmesini bekle
            try:
                self.wait.until(EC.presence_of_element_located((By.CLASS_NAME, "visa-card-container")))
            except TimeoutException:
                self.log_message.emit("Visa kartları yüklenemedi")
                return False
            
            # Sayfa kaynağını al ve parse et
            page_source = self.driver.page_source
            soup = BeautifulSoup(page_source, 'html.parser')
            
            # Visa kartlarını bul
            visa_cards = soup.find_all('div', class_='visa-card-container')
            self.log_message.emit(f"Bulunan visa kartı sayısı: {len(visa_cards)}")
            
            # İstenen kriterlere göre filtrele
            for i, card in enumerate(visa_cards, 1):
                self.log_message.emit(f"\nKart {i} kontrol ediliyor...")
                
                # Durum kontrolü - büyük/küçük harf duyarsız
                status = card.select_one('.status-text')
                if not status:
                    self.log_message.emit(f"Kart {i}: Durum bilgisi bulunamadı")
                    continue
                    
                status_text = status.text.strip()
                self.log_message.emit(f"Kart {i} Durum: {status_text}")
                
                if self.user_info.visa_status.lower() not in status_text.lower():
                    self.log_message.emit(f"Kart {i}: Durum eşleşmedi (Aranan: {self.user_info.visa_status}, Bulunan: {status_text})")
                    continue
                
                # Konum kontrolü - tam rota
                country_mission = card.select_one('.country-mission-row')
                if not country_mission:
                    self.log_message.emit(f"Kart {i}: Rota bilgisi bulunamadı")
                    continue
                    
                route_text = country_mission.text.strip()
                self.log_message.emit(f"Kart {i} Rota: {route_text}")
                
                if "Turkey → France" not in route_text:
                    self.log_message.emit(f"Kart {i}: Rota eşleşmedi (Aranan: Turkey → France, Bulunan: {route_text})")
                    continue
                
                # Kategori ve tip kontrolü
                details = card.select('.visa-details .line')
                category_match = False
                type_match = False
                
                self.log_message.emit(f"Kart {i} Detaylar:")
                for detail in details:
                    text = detail.get_text(strip=True)
                    self.log_message.emit(f"  - {text}")
                    
                    text_lower = text.lower()
                    if 'category' in text_lower:
                        if self.user_info.visa_category.lower() in text_lower:
                            category_match = True
                            self.log_message.emit(f"  Kategori eşleşti: {text}")
                        else:
                            self.log_message.emit(f"  Kategori eşleşmedi (Aranan: {self.user_info.visa_category}, Bulunan: {text})")
                            
                    if 'type' in text_lower:
                        if self.user_info.visa_type.lower() in text_lower:
                            type_match = True
                            self.log_message.emit(f"  Tip eşleşti: {text}")
                        else:
                            self.log_message.emit(f"  Tip eşleşmedi (Aranan: {self.user_info.visa_type}, Bulunan: {text})")
                
                if category_match and type_match:
                    self.log_message.emit(f"\nUygun randevu bulundu! (Kart {i})")
                    self.log_message.emit(f"Durum: {status_text}")
                    self.log_message.emit(f"Rota: {route_text}")
                    for detail in details:
                        self.log_message.emit(detail.get_text(strip=True))
                    return True
                else:
                    self.log_message.emit(f"Kart {i}: Kategori veya tip eşleşmedi (Kategori: {category_match}, Tip: {type_match})")
            
            self.log_message.emit("\nUygun randevu bulunamadı")
            return False
            
        except Exception as e:
            self.log_message.emit(f"Randevu kontrolü sırasında hata: {str(e)}")
            return False

    def wait_for_available_appointment(self):
        """Sürekli olarak randevu kontrolü yap"""
        check_interval = self.user_info.check_interval
        
        while self.is_running:
            if self.check_visa_availability():
                self.log_message.emit("Randevu bulundu! İşleme devam ediliyor...")
                return True
                
            self.log_message.emit(f"{check_interval} saniye sonra tekrar kontrol edilecek...")
            
            # Belirtilen süre kadar bekle
            for _ in range(check_interval):
                if not self.is_running:
                    return False
                time.sleep(1)
        
        return False

    def run(self):
        try:
            self.setup_driver()
            
            # Check visa availability if switch is enabled
            if self.user_info.check_visa_switch == "Evet":
                # Randevu bulunana kadar bekle
                if not self.wait_for_available_appointment():
                    self.log_message.emit("İşlem kullanıcı tarafından durduruldu")
                    return
            else:
                self.log_message.emit("Web sitesinden vize kontrolü devre dışı, doğrudan işlemlere başlanıyor...")
                
            self.login_process()
            self.booking_process()
            self.status_changed.emit(BookingStatus.COMPLETED.value)
            self.booking_completed.emit()
        except Exception as e:
            self.error_occurred.emit(f"Hata oluştu: {str(e)}")
            self.log_message.emit(f"HATA: {str(e)}")
        finally:
            self.log_message.emit("İşlem tamamlandı, kaynaklar temizleniyor...")

    def setup_driver(self):
        self.status_changed.emit(BookingStatus.LOGGING_IN.value)
        self.log_message.emit("Tarayıcı başlatılıyor...")
        self.progress_changed.emit(10)
    
        options = uc.ChromeOptions()
        options.add_argument("--user-data-dir=chrome-data")
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.headless = False
        
        self.driver = uc.Chrome()
        self.driver.maximize_window()
        self.wait = WebDriverWait(self.driver, 20)
        
        self.log_message.emit("Tarayıcı başarıyla başlatıldı")
        self.progress_changed.emit(20)

    def login_process(self):
        self.log_message.emit("Giriş sayfasına yönlendiriliyor...")
        self.driver.get("https://visa.vfsglobal.com/tur/tr/fra/login")
        
        # Check for queue page first
        self.handle_queue_page()
        
        time.sleep(10)
        self.progress_changed.emit(30)

        # Cookie handling
        try:
            cerez = self.wait.until(EC.presence_of_element_located((By.ID, "onetrust-reject-all-handler")))
            self.click_element(cerez)
            self.log_message.emit("Çerezler reddedildi")
        except TimeoutException:
            self.log_message.emit("Çerez butonu bulunamadı")

        # Login credentials
        self.log_message.emit("Giriş bilgileri giriliyor...")
        try:
            username = self.wait.until(EC.presence_of_element_located((By.ID, "email")))
            username.clear()
            username.send_keys(self.user_info.email)

            password = self.wait.until(EC.presence_of_element_located((By.ID, "password")))
            password.clear()
            password.send_keys(self.user_info.password)

            self.log_message.emit("Giriş bilgileri girildi")
            self.progress_changed.emit(40)

            # Submit login
            if not self.click_button("Oturum Aç"):
                raise Exception("Giriş butonu tıklanamadı")

            time.sleep(2)  # Allow time for login to process
            
            # SMS verification
            self.input_required.emit("SMS Kodu", "Lütfen SMS kodunu girin:")
            self.input_event = self.wait_for_input()
            self.input_event.wait()
            
            sms_input = self.wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "input[placeholder='**********']")))
            sms_input.clear()
            sms_input.send_keys(self.user_input)
            
            if not self.click_button("Doğrula"):
                self.log_message.emit("SMS kodu girilemedi")
                self.input_required.emit("Manuel Giriş", "Lütfen kendiniz giriş yapıp onaylayın. Tamam'a bastıktan sonra işlem devam edecektir.")
                self.input_event = self.wait_for_input()
                self.input_event.wait()
                self.log_message.emit("Manuel giriş onaylandı, devam ediliyor...")

        except Exception as e:
            self.log_message.emit(f"Giriş işlemi sırasında hata: {str(e)}")
            self.input_required.emit("Manuel Giriş", "Lütfen kendiniz giriş yapıp onaylayın. Tamam'a bastıktan sonra işlem devam edecektir.")
            self.input_event = self.wait_for_input()
            self.input_event.wait()
            self.log_message.emit("Manuel giriş onaylandı, devam ediliyor...")
            time.sleep(2)
            self.progress_changed.emit(40)

    def booking_process(self):
        self.driver.get("https://visa.vfsglobal.com/tur/tr/fra/dashboard")
        time.sleep(2)
        self.status_changed.emit(BookingStatus.FINDING_APPOINTMENT.value)
        self.log_message.emit("Reservasyon butonu aranıyor...")
        time.sleep(5)

        def rezervasyon_click():
            try:
                buttons = self.wait.until(
                    EC.presence_of_all_elements_located((
                        By.XPATH, "//*[@class='mdc-button__label' and contains(text(), 'Yeni Rezervasyon Başlat')]"
                    ))
                )
                print(f"Bulunan buton sayısı: {len(buttons)}")
                # Görünür olanı bul ve tıkla
                
                ActionChains(self.driver).move_to_element(buttons[-1]).click().perform()
                        
                self.progress_changed.emit(60)
                self.log_message.emit("Yeni rezervasyon sayfasına yönlendirildi")
            except:
                self.log_message.emit("Yeni rezervasyon sayfası bulunamadı")
                time.sleep(3)
                try:
                    rezervasyon_click()
                except:
                    self.log_message.emit("Yeni rezervasyon sayfası hala bulunamadı, lütfen manuel olarak kontrol edin")
                    self.error_occurred.emit("Yeni rezervasyon sayfası hala bulunamadı, lütfen manuel olarak kontrol edin")
        rezervasyon_click()

        time.sleep(3)
        try:
            self.select_booking_options()
        except Exception as e:
            self.log_message.emit(f"Rezervasyon seçenekleri ayarlanamadı: {str(e)}")
            self.error_occurred.emit("Rezervasyon seçenekleri ayarlanamadı")
            return
        time.sleep(10)
        # Check appointment availability
        try:
            mesaj = self.wait.until(EC.element_to_be_clickable((By.CLASS_NAME, "alert"))).text
            if "Üzgünüz" in mesaj:
                self.log_message.emit("Randevu bulunamadı! İşlemler yeniden başlatılıyor...")
                self.error_occurred.emit("Randevu bulunamadı!")
                self.play_queue_notification()
                self.booking_process()
                self.log_message.emit(f"{self.wait_time} saniye bekleniyor...")
                time.sleep(self.wait_time)
                return False
            else:
                self.log_message.emit(f"Randevu bulundu: {mesaj}")
                self.play_queue_notification()
        except TimeoutException:
            self.log_message.emit("Randevu durumu kontrol edilemedi")

        self.progress_changed.emit(70)
        self.continue_booking()

    def select_booking_options(self):
        """Select booking center and service options"""
        self.log_message.emit("Rezervasyon seçenekleri ayarlanıyor...")
        time.sleep(3)  # Allow time for page to load
        # Center selection
        try:    
            center_select = self.wait.until(EC.element_to_be_clickable((By.ID, "mat-select-0")))
            center_select.click()
            istanbul_option = self.wait.until(EC.element_to_be_clickable((By.XPATH, "//*[@id='IBY']")))
            istanbul_option.click()
            time.sleep(3) # Allow time for options to load
        except:  
            try:
                center_select = self.wait.until(EC.element_to_be_clickable((By.ID, "mat-select-0")))
                center_select.click()
                istanbul_option = self.wait.until(EC.element_to_be_clickable((By.XPATH, "//*[@id='IBY']")))
                istanbul_option.click()
                time.sleep(3) 
            except:
                self.booking_process()
        # Service selection
        try:
            center_select = self.wait.until(EC.element_to_be_clickable((By.ID, "mat-select-4")))
            center_select.click()
            service_option = self.wait.until(EC.element_to_be_clickable((By.XPATH, "//*[@id='SSV']")))
            service_option.click()
            time.sleep(3)  # Allow time for options to load

        except:
            try:
                center_select = self.wait.until(EC.element_to_be_clickable((By.ID, "mat-select-4")))
                center_select.click()
                service_option = self.wait.until(EC.element_to_be_clickable((By.XPATH, "//*[@id='SSV']")))
                service_option.click()
                time.sleep(3)  # Allow time for options to load
            except:
                self.booking_process()

        # Duration selection
        try:
            center_select = self.wait.until(EC.element_to_be_clickable((By.ID, "mat-select-2")))
            center_select.click()
            duration_option = self.wait.until(EC.element_to_be_clickable((By.XPATH, "//*[@id='SHORSTD']")))
            duration_option.click()
            time.sleep(3)  # Allow time for options to load
        except:
            try:
                center_select = self.wait.until(EC.element_to_be_clickable((By.ID, "mat-select-2")))
                center_select.click()
                duration_option = self.wait.until(EC.element_to_be_clickable((By.XPATH, "//*[@id='SHORSTD']")))
                duration_option.click()
                time.sleep(3)
            except:
                self.booking_process()


    def continue_booking(self):
        """Continue with personal information form"""
        self.status_changed.emit(BookingStatus.FILLING_FORM.value)
        self.log_message.emit("Kişisel bilgiler formu dolduruluyor...")
        
        if not self.click_button("Devam Et"):
            raise Exception("Devam Et butonu tıklanamadı")
        
        # Fill personal information
        self.fill_personal_info()
        
        if not self.click_button("Kaydet"):
            raise Exception("Kaydet butonu tıklanamadı")
            
        if not self.click_button("Devam Et"):
            raise Exception("Devam Et butonu tıklanamadı")
        
        self.progress_changed.emit(80)
        self.complete_booking()

    def fill_personal_info(self):
        """Fill personal information form"""
        time.sleep(3)
        try:
            # Reference number
            ref_input = self.wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "input[placeholder='Referans numaranızı giriniz']")))
            ref_input.send_keys(self.user_info.reference_number)
        except:
            try:
                time.sleep(1)
                ref_input = self.wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "input[placeholder='Referans numaranızı giriniz']")))
                ref_input.send_keys(self.user_info.reference_number)
            except:
                self.driver.refresh()
                self.fill_personal_info()
                return

        time.sleep(3)
        # Name and surname
        try:
            name_input = self.wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "input[placeholder='İsminizi Giriniz']")))
            name_input.send_keys(self.user_info.first_name)
        except:
            try:
                time.sleep(1)
                name_input = self.wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "input[placeholder='İsminizi Giriniz']")))
                name_input.send_keys(self.user_info.first_name)
            except:
                self.driver.refresh()
                self.fill_personal_info()
                return

        time.sleep(3)
        try:
            surname_input = self.wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "input[placeholder='Lütfen soy isminizi giriniz.']")))
            surname_input.send_keys(self.user_info.last_name)
        except:
            try:
                time.sleep(1)
                surname_input = self.wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "input[placeholder='Lütfen soy isminizi giriniz.']")))
                surname_input.send_keys(self.user_info.last_name)
            except:
                self.driver.refresh()
                self.fill_personal_info()
                return

        time.sleep(3)
        # Gender
        try:
            gender_select = self.wait.until(EC.element_to_be_clickable((By.XPATH, "(//mat-select)[1]")))
            gender_select.click()
            time.sleep(1)
            gender_option = self.wait.until(EC.element_to_be_clickable((By.XPATH, f"//*[@class='mdc-list-item__primary-text' and contains(text(), '{self.user_info.gender}')]")))
            gender_option.click()
        except:
            try:
                time.sleep(1)
                gender_select = self.wait.until(EC.element_to_be_clickable((By.XPATH, "(//mat-select)[1]")))
                gender_select.click()
                time.sleep(1)
                gender_option = self.wait.until(EC.element_to_be_clickable((By.XPATH, f"//*[@class='mdc-list-item__primary-text' and contains(text(), '{self.user_info.gender}')]")))
                gender_option.click()
            except:
                self.driver.refresh()
                self.fill_personal_info()
                return

        time.sleep(3)
        # Birth date
        try:
            birth_input = self.wait.until(EC.element_to_be_clickable((By.ID, "dateOfBirth")))
            birth_input.send_keys(self.user_info.birth_date)
        except:
            try:
                time.sleep(1)
                birth_input = self.wait.until(EC.element_to_be_clickable((By.ID, "dateOfBirth")))
                birth_input.send_keys(self.user_info.birth_date)
            except:
                self.driver.refresh()
                self.fill_personal_info()
                return

        time.sleep(3)
        # Nationality
        try:
            nationality_select = self.wait.until(EC.element_to_be_clickable((By.XPATH, "(//mat-select)[2]")))
            nationality_select.click()
            time.sleep(1)
            nationality_option = self.wait.until(EC.element_to_be_clickable((By.XPATH, f"//*[@class='mdc-list-item__primary-text' and contains(text(), '{self.user_info.nationality}')]")))
            nationality_option.click()
        except:
            try:
                time.sleep(1)
                nationality_select = self.wait.until(EC.element_to_be_clickable((By.XPATH, "(//mat-select)[2]")))
                nationality_select.click()
                time.sleep(1)
                nationality_option = self.wait.until(EC.element_to_be_clickable((By.XPATH, f"//*[@class='mdc-list-item__primary-text' and contains(text(), '{self.user_info.nationality}')]")))
                nationality_option.click()
            except:
                self.driver.refresh()
                self.fill_personal_info()
                return

        time.sleep(3)
        # Passport information
        try:
            passport_input = self.wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "input[placeholder='pasaport Numarası Giriniz']")))
            passport_input.send_keys(self.user_info.passport_number)
        except:
            try:
                time.sleep(1)
                passport_input = self.wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "input[placeholder='pasaport Numarası Giriniz']")))
                passport_input.send_keys(self.user_info.passport_number)
            except:
                self.driver.refresh()
                self.fill_personal_info()
                return

        time.sleep(3)
        try:
            expiry_input = self.wait.until(EC.element_to_be_clickable((By.ID, "passportExpirtyDate")))
            expiry_input.send_keys(self.user_info.passport_expiry)
        except:
            try:
                time.sleep(1)
                expiry_input = self.wait.until(EC.element_to_be_clickable((By.ID, "passportExpirtyDate")))
                expiry_input.send_keys(self.user_info.passport_expiry)
            except:
                self.driver.refresh()
                self.fill_personal_info()
                return

        time.sleep(3)
        self.log_message.emit("Kişisel bilgiler başarıyla dolduruldu")

    def complete_booking(self):
        """Complete the booking process"""
        self.log_message.emit("Rezervasyon tamamlanıyor...")
        
        if not self.click_button("Tek Seferlik Şifre (OTP) Oluştur"):
            raise Exception("OTP oluşturma butonu tıklanamadı")
        
        # Get OTP from user
        self.input_required.emit("OTP Kodu", "OTP kodunu giriniz:")
        self.input_event = self.wait_for_input()
        self.input_event.wait()
        
        otp_input = self.wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "input[placeholder='OTP']")))
        otp_input.clear()
        otp_input.send_keys(self.user_input)
        
        if not self.click_button("Doğrula"):
            raise Exception("OTP doğrulama butonu tıklanamadı")
            
        if not self.click_button("Devam Et"):
            raise Exception("Devam Et butonu tıklanamadı")
        
        # Select date and time
        date_element = self.wait.until(EC.element_to_be_clickable((By.CLASS_NAME, "date-availiable")))
        if not self.click_element(date_element):
            raise Exception("Tarih seçilemedi")
            
        radio_element = self.wait.until(EC.presence_of_element_located((By.ID, "STRadio1")))
        if not self.click_element(radio_element):
            raise Exception("Saat seçilemedi")
        
        if not self.click_button("Devam Et"):
            raise Exception("Devam Et butonu tıklanamadı")
            
        if not self.click_button("Devam Et"):
            raise Exception("Devam Et butonu tıklanamadı")
        
        self.progress_changed.emit(100)
        self.log_message.emit("Rezervasyon başarıyla tamamlandı!")

    def handle_queue_page(self):
        """Handle virtual queue page if it appears"""
        try:
            # Check if we're on the queue page
            queue_title = self.driver.find_element(By.XPATH, "//*[contains(text(), 'You are now in line')]")
            if queue_title:
                self.log_message.emit("Sanal kuyrukta bekliyoruz...")
                self.status_changed.emit("Sanal kuyrukta bekliyor")
                
                # Initial refresh when entering queue
                self.log_message.emit("Kuyruk sayfası yenileniyor...")
                
                time.sleep(10)  # Wait for page to reload
                self.driver.refresh()
                time.sleep(2)
                # Extract wait time if available
                try:
                    wait_time_element = self.driver.find_element(By.XPATH, "//*[contains(text(), 'estimated wait time')]")
                    wait_time_text = wait_time_element.text
                    # Extract numeric value from text
                    import re
                    wait_minutes = re.search(r'(\d+\.?\d*)', wait_time_text)
                    if wait_minutes:
                        wait_time = float(wait_minutes.group(1))
                        self.log_message.emit(f"Tahmini bekleme süresi: {wait_time:.1f} dakika")
                        
                        # If wait time is too long (more than 30 minutes), refresh the page
                        if wait_time > 30:
                            self.log_message.emit("Bekleme süresi çok uzun, sayfa yenileniyor...")
                            # Clear cookies
                            self.driver.delete_all_cookies()
                            # Refresh the page
                            self.driver.refresh()
                            time.sleep(5)  # Wait for page to reload
                            return  # Exit the method to start fresh
                        
                        # Calculate check intervals based on wait time
                        if wait_time > 10:
                            check_interval = 30  # Check every 30 seconds for long waits
                        elif wait_time > 5:
                            check_interval = 15  # Check every 15 seconds for medium waits
                        else:
                            check_interval = 5   # Check every 5 seconds for short waits
                    else:
                        check_interval = 10  # Default interval
                        
                except Exception:
                    check_interval = 10  # Default if we can't extract time
                    self.log_message.emit("Bekleme süresi tespit edilemedi, varsayılan kontrol aralığı kullanılıyor")
                
                # Wait for the queue to clear
                queue_cleared = False
                wait_count = 0
                max_wait_cycles = 500  # Prevent infinite loop (about 16 minutes with 10s intervals)
                
                while not queue_cleared and wait_count < max_wait_cycles and self.is_running:
                    try:
                        # Check if we're still in queue
                        still_in_queue = "Waiting Room" in self.driver.page_source
                        
                        if not still_in_queue:
                            # Queue cleared, we can proceed
                            queue_cleared = True
                            self.log_message.emit("Sanal kuyruk geçildi, siteye erişim sağlandı")
                            self.status_changed.emit("Siteye erişim sağlandı")
                            break
                        
                        # Update wait information
                        try:
                            # Get updated wait time
                            wait_time_element = self.driver.find_element(By.XPATH, "//*[contains(text(), 'estimated wait time')]")
                            current_wait = wait_time_element.text
                            self.log_message.emit(f"Kuyrukta bekleniyor... {current_wait}")
                            
                            # Get last updated time
                            last_updated = self.driver.find_element(By.XPATH, "//*[contains(text(), 'Last updated')]")
                            self.log_message.emit(f"Son güncelleme: {last_updated.text}")
                            
                        except Exception:
                            self.log_message.emit(f"Kuyrukta bekleniyor... ({wait_count * check_interval} saniye geçti)")
                        
                        # Wait before next check
                        for i in range(check_interval):
                            if not self.is_running:
                                return
                            time.sleep(1)
                        
                        wait_count += 1
                        
                    except Exception as e:
                        self.log_message.emit(f"Kuyruk kontrolü sırasında hata: {str(e)}")
                        time.sleep(5)
                        wait_count += 1
                
                if not queue_cleared and wait_count >= max_wait_cycles:
                    self.log_message.emit("Maksimum bekleme süresine ulaşıldı, devam etmeye çalışılıyor...")
                    
        except NoSuchElementException:
            # Not on queue page, continue normally
            self.log_message.emit("Sanal kuyruk sayfası tespit edilmedi, normal işleme devam ediliyor")
        except Exception as e:
            self.log_message.emit(f"Kuyruk kontrolü sırasında beklenmeyen hata: {str(e)}")

    def get_element_center(self, element):
        """Get center coordinates of an element"""
        location = element.location
        size = element.size
        x = location['x'] + size['width'] // 2
        y = location['y'] + size['height'] // 2
        return x, y

    def wait_for_input(self):
        """Wait for user input"""
        from threading import Event
        event = Event()
        return event

    def set_user_input(self, input_text):
        """Set user input and signal the worker"""
        self.user_input = input_text
        self.input_received.emit(input_text)
        if self.input_event:
            self.input_event.set()

    def cleanup(self):
        """Clean up resources"""
        if self.driver:
            # self.driver.quit()  # Tarayıcıyı kapatmayı engelliyoruz
            self.log_message.emit("Tarayıcı oturumu korunuyor")

    def stop(self):
        """Stop the worker"""
        self.is_running = False
        # self.terminate()  # Thread'i sonlandırmayı engelliyoruz
        self.log_message.emit("İşlem durduruldu, tarayıcı oturumu korunuyor")

    def play_queue_notification(self):
        """Sıra bittiğinde sesli uyarı çalar"""
        # 3 kez bip sesi çal (1000Hz, her biri 500ms)
        try:
            for _ in range(3):
                winsound.Beep(1000, 500)
                time.sleep(0.2)  # Bipler arası kısa bekleme
        except:
            pass

    def click_button(self, button_text, max_attempts=2, wait_time=3):
        """Try to click a button with given text, with retry mechanism"""
        for attempt in range(max_attempts):
            try:
                button = self.wait.until(EC.element_to_be_clickable((By.XPATH, f"//*[@class='mdc-button__label' and contains(text(), '{button_text}')]")))
                ActionChains(self.driver).move_to_element(button).click().perform()
                self.log_message.emit(f"'{button_text}' butonuna tıklandı")
                time.sleep(wait_time)
                return True
            except Exception as e:
                if attempt < max_attempts - 1:
                    self.log_message.emit(f"'{button_text}' butonuna tıklama denemesi {attempt + 1} başarısız, yeniden deneniyor...")
                    time.sleep(wait_time)
                else:
                    self.log_message.emit(f"'{button_text}' butonuna tıklanamadı: {str(e)}")
                    return False
        return False

    def click_element(self, element, max_attempts=2, wait_time=3):
        """Try to click an element with retry mechanism"""
        for attempt in range(max_attempts):
            try:
                ActionChains(self.driver).move_to_element(element).click().perform()
                time.sleep(wait_time)
                return True
            except Exception as e:
                if attempt < max_attempts - 1:
                    self.log_message.emit(f"Element tıklama denemesi {attempt + 1} başarısız, yeniden deneniyor...")
                    time.sleep(wait_time)
                else:
                    self.log_message.emit(f"Element tıklanamadı: {str(e)}")
                    return False
        return False

class ModernVisaBookingApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.user_info = UserInfo.load_from_file()  # Load saved information when starting
        self.worker = None
        self.wait_time = 180  # Default wait time in seconds
        self.setup_ui()
        self.setup_style()
        self.load_saved_info()  # Load saved information into UI

    def setup_ui(self):
        self.setWindowTitle("Modern Visa Randevu Sistemi")
        self.setGeometry(100, 100, 1200, 800)
        self.setMinimumSize(1000, 700)

        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # Main layout
        main_layout = QHBoxLayout(central_widget)
        
        # Create splitter
        splitter = QSplitter(Qt.Horizontal)
        main_layout.addWidget(splitter)

        # Left panel - Configuration
        left_panel = self.create_config_panel()
        splitter.addWidget(left_panel)

        # Right panel - Monitoring
        right_panel = self.create_monitoring_panel()
        splitter.addWidget(right_panel)

        # Set splitter proportions
        splitter.setSizes([400, 600])

    def create_config_panel(self):
        """Create configuration panel"""
        panel = QWidget()
        layout = QVBoxLayout(panel)

        # Title
        title = QLabel("Yapılandırma")
        title.setFont(QFont("Arial", 16, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        # Tabs
        tab_widget = QTabWidget()
        
        # Login tab
        login_tab = QWidget()
        login_layout = QFormLayout(login_tab)
        
        self.email_input = QLineEdit()
        self.email_input.setPlaceholderText("email@example.com")
        login_layout.addRow("E-posta:", self.email_input)
        
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.Password)
        login_layout.addRow("Şifre:", self.password_input)
        
        tab_widget.addTab(login_tab, "Giriş Bilgileri")

        # Personal info tab
        personal_tab = QWidget()
        personal_layout = QFormLayout(personal_tab)
        
        self.first_name_input = QLineEdit()
        personal_layout.addRow("Ad:", self.first_name_input)
        
        self.last_name_input = QLineEdit()
        personal_layout.addRow("Soyad:", self.last_name_input)
        
        self.gender_combo = QComboBox()
        self.gender_combo.addItems(["Male", "Female"])
        personal_layout.addRow("Cinsiyet:", self.gender_combo)
        
        self.birth_date_input = QLineEdit()
        self.birth_date_input.setPlaceholderText("DDMMYYYY")
        personal_layout.addRow("Doğum Tarihi:", self.birth_date_input)
        
        self.nationality_combo = QComboBox()
        self.nationality_combo.addItems(["Türkiye", "Other"])
        personal_layout.addRow("Uyrukluk:", self.nationality_combo)
        
        tab_widget.addTab(personal_tab, "Kişisel Bilgiler")

        # Passport tab
        passport_tab = QWidget()
        passport_layout = QFormLayout(passport_tab)
        
        self.passport_number_input = QLineEdit()
        passport_layout.addRow("Pasaport No:", self.passport_number_input)
        
        self.passport_expiry_input = QLineEdit()
        self.passport_expiry_input.setPlaceholderText("DDMMYYYY")
        passport_layout.addRow("Pasaport Bitiş:", self.passport_expiry_input)
        
        self.reference_input = QLineEdit()
        passport_layout.addRow("Referans No:", self.reference_input)
        
        tab_widget.addTab(passport_tab, "Pasaport Bilgileri")

        # Settings tab
        settings_tab = QWidget()
        settings_layout = QFormLayout(settings_tab)
        
        # Visa search settings
        self.visa_status_input = QLineEdit()
        self.visa_status_input.setPlaceholderText("open")
        settings_layout.addRow("Vize Durumu:", self.visa_status_input)
        
        self.visa_location_input = QLineEdit()
        self.visa_location_input.setPlaceholderText("Istanbul Beyoglu")
        settings_layout.addRow("Vize Konumu:", self.visa_location_input)
        
        self.visa_category_input = QLineEdit()
        self.visa_category_input.setPlaceholderText("Short Term")
        settings_layout.addRow("Vize Kategorisi:", self.visa_category_input)
        
        self.visa_type_input = QLineEdit()
        self.visa_type_input.setPlaceholderText("Short Term Standard")
        settings_layout.addRow("Vize Tipi:", self.visa_type_input)
        
        # Add check visa availability switch
        self.check_visa_switch = QComboBox()
        self.check_visa_switch.addItems(["Evet", "Hayır"])
        settings_layout.addRow("Web Sitesinden Vize Kontrolü:", self.check_visa_switch)
        
        self.check_interval_input = QLineEdit()
        self.check_interval_input.setPlaceholderText("30")
        settings_layout.addRow("Kontrol Aralığı (saniye):", self.check_interval_input)
        
        self.wait_time_input = QLineEdit()
        self.wait_time_input.setPlaceholderText("180")
        settings_layout.addRow("Bekleme Süresi (saniye):", self.wait_time_input)
        
        tab_widget.addTab(settings_tab, "Ayarlar")

        layout.addWidget(tab_widget)

        # Control buttons
        button_layout = QVBoxLayout()
        
        self.start_button = QPushButton("Randevu Aramayı Başlat")
        self.start_button.clicked.connect(self.start_booking)
        self.start_button.setMinimumHeight(40)
        button_layout.addWidget(self.start_button)
        
        self.stop_button = QPushButton("Durdur")
        self.stop_button.clicked.connect(self.stop_booking)
        self.stop_button.setEnabled(False)
        self.stop_button.setMinimumHeight(40)
        button_layout.addWidget(self.stop_button)
        
        layout.addLayout(button_layout)
        layout.addStretch()

        return panel

    def create_monitoring_panel(self):
        """Create monitoring panel"""
        panel = QWidget()
        layout = QVBoxLayout(panel)

        # Title
        title = QLabel("İzleme Paneli")
        title.setFont(QFont("Arial", 16, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        # Status group
        status_group = QGroupBox("Durum")
        status_layout = QVBoxLayout(status_group)
        
        self.status_label = QLabel("Beklemede")
        self.status_label.setFont(QFont("Arial", 12, QFont.Bold))
        self.status_label.setAlignment(Qt.AlignCenter)
        status_layout.addWidget(self.status_label)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(100)
        status_layout.addWidget(self.progress_bar)
        
        layout.addWidget(status_group)

        # Log group
        log_group = QGroupBox("Sistem Logları")
        log_layout = QVBoxLayout(log_group)
        
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setFont(QFont("Consolas", 9))
        log_layout.addWidget(self.log_text)
        
        # Clear log button
        clear_button = QPushButton("Logları Temizle")
        clear_button.clicked.connect(self.clear_logs)
        log_layout.addWidget(clear_button)
        
        layout.addWidget(log_group)

        return panel

    def setup_style(self):
        """Setup modern dark theme"""
        self.setStyleSheet("""
            QMainWindow {
                background-color: #2b2b2b;
                color: #ffffff;
            }
            QWidget {
                background-color: #2b2b2b;
                color: #ffffff;
            }
            QGroupBox {
                font-weight: bold;
                border: 2px solid #555555;
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
            QLineEdit {
                background-color: #404040;
                border: 2px solid #555555;
                border-radius: 6px;
                padding: 8px;
                font-size: 12px;
            }
            QLineEdit:focus {
                border-color: #0078d4;
            }
            QComboBox {
                background-color: #404040;
                border: 2px solid #555555;
                border-radius: 6px;
                padding: 8px;
                font-size: 12px;
            }
            QComboBox:focus {
                border-color: #0078d4;
            }
            QPushButton {
                background-color: #0078d4;
                border: none;
                border-radius: 6px;
                padding: 10px;
                font-size: 12px;
                font-weight: bold;
                color: white;
            }
            QPushButton:hover {
                background-color: #106ebe;
            }
            QPushButton:pressed {
                background-color: #005a9e;
            }
            QPushButton:disabled {
                background-color: #555555;
                color: #888888;
            }
            QTextEdit {
                background-color: #1e1e1e;
                border: 2px solid #555555;
                border-radius: 6px;
                padding: 8px;
                font-family: 'Consolas', monospace;
                font-size: 10px;
            }
            QTabWidget::pane {
                border: 2px solid #555555;
                border-radius: 6px;
            }
            QTabWidget::tab-bar {
                alignment: center;
            }
            QTabBar::tab {
                background-color: #404040;
                border: 1px solid #555555;
                padding: 8px 16px;
                margin-right: 2px;
            }
            QTabBar::tab:selected {
                background-color: #0078d4;
                border-color: #0078d4;
            }
            QProgressBar {
                border: 2px solid #555555;
                border-radius: 6px;
                text-align: center;
                font-weight: bold;
            }
            QProgressBar::chunk {
                background-color: #0078d4;
                border-radius: 4px;
            }
            QLabel {
                color: #ffffff;
            }
            QSplitter::handle {
                background-color: #555555;
                width: 3px;
            }
        """)

    def update_wait_time(self):
        """Update wait time from input"""
        try:
            new_wait_time = int(self.wait_time_input.text())
            if new_wait_time > 0:
                self.wait_time = new_wait_time
                self.add_log(f"Bekleme süresi {self.wait_time} saniye olarak güncellendi")
        except ValueError:
            self.wait_time_input.setText(str(self.wait_time))

    def start_booking(self):
        """Start the booking process"""
        # Validate inputs
        if not self.validate_inputs():
            return

        # Collect user information
        self.collect_user_info()

        # Create and start worker
        self.worker = VisaBookingWorker(self.user_info)
        self.worker.wait_time = self.wait_time  # Set wait time
        self.worker.status_changed.connect(self.update_status)
        self.worker.progress_changed.connect(self.update_progress)
        self.worker.log_message.connect(self.add_log)
        self.worker.input_required.connect(self.show_input_dialog)
        self.worker.error_occurred.connect(self.show_error)
        self.worker.booking_completed.connect(self.booking_completed)
        
        self.worker.start()
        
        # Update UI
        self.start_button.setEnabled(False)
        self.stop_button.setEnabled(True)
        self.add_log("Randevu arama işlemi başlatıldı...")

    def validate_inputs(self):
        """Validate user inputs"""
        if not self.email_input.text():
            QMessageBox.warning(self, "Uyarı", "E-posta adresi gerekli!")
            return False
        if not self.password_input.text():
            QMessageBox.warning(self, "Uyarı", "Şifre gerekli!")
            return False
        if not self.first_name_input.text():
            QMessageBox.warning(self, "Uyarı", "Ad gerekli!")
            return False
        if not self.last_name_input.text():
            QMessageBox.warning(self, "Uyarı", "Soyad gerekli!")
            return False
        return True

    def collect_user_info(self):
        """Collect user information from inputs"""
        self.user_info.email = self.email_input.text()
        self.user_info.password = self.password_input.text()
        self.user_info.first_name = self.first_name_input.text()
        self.user_info.last_name = self.last_name_input.text()
        self.user_info.gender = self.gender_combo.currentText()
        self.user_info.birth_date = self.user_info.format_date(self.birth_date_input.text())
        self.user_info.nationality = self.nationality_combo.currentText()
        self.user_info.passport_number = self.passport_number_input.text()
        self.user_info.passport_expiry = self.user_info.format_date(self.passport_expiry_input.text())
        self.user_info.reference_number = self.reference_input.text()
        
        # Visa search settings
        self.user_info.visa_status = self.visa_status_input.text() or "open"
        self.user_info.visa_location = self.visa_location_input.text() or "Istanbul Beyoglu"
        self.user_info.visa_category = self.visa_category_input.text() or "Short Term"
        self.user_info.visa_type = self.visa_type_input.text() or "Short Term Standard"
        self.user_info.check_visa_switch = self.check_visa_switch.currentText()
        try:
            self.user_info.check_interval = int(self.check_interval_input.text() or "30")
        except ValueError:
            self.user_info.check_interval = 30
        try:
            self.user_info.wait_time = int(self.wait_time_input.text() or "180")
        except ValueError:
            self.user_info.wait_time = 180
        
        # Save the information after collecting
        if self.user_info.save_to_file():
            self.add_log("Bilgiler başarıyla kaydedildi")
        else:
            self.add_log("Bilgiler kaydedilirken hata oluştu")

    def stop_booking(self):
        """Stop the booking process"""
        if self.worker:
            self.worker.stop()
            self.worker = None
        
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        self.add_log("Randevu arama işlemi durduruldu")

    def update_status(self, status):
        """Update status label"""
        self.status_label.setText(status)

    def update_progress(self, value):
        """Update progress bar"""
        self.progress_bar.setValue(value)

    def add_log(self, message):
        """Add log message"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        formatted_message = f"[{timestamp}] {message}"
        self.log_text.append(formatted_message)

    def clear_logs(self):
        """Clear log messages"""
        self.log_text.clear()

    def show_input_dialog(self, title, prompt):
        """Show input dialog for user input"""
        text, ok = QInputDialog.getText(self, title, prompt)
        if ok and self.worker:
            self.worker.set_user_input(text)

    def show_error(self, error_message):
        """Show error message"""
        QMessageBox.critical(self, "Hata", error_message)
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)

    def booking_completed(self):
        """Handle booking completion"""
        QMessageBox.information(self, "Başarılı", "Randevu işlemi başarıyla tamamlandı!")
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)

    def closeEvent(self, event):
        """Handle window close event"""
        if self.worker and self.worker.isRunning():
            reply = QMessageBox.question(
                self, 'Çıkış', 
                'Randevu arama işlemi devam ediyor. Çıkmak istediğinizden emin misiniz?',
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            
            if reply == QMessageBox.Yes:
                self.worker.stop()
                event.accept()
            else:
                event.ignore()
        else:
            event.accept()

    def load_saved_info(self):
        """Load saved information into UI fields"""
        self.email_input.setText(self.user_info.email)
        self.password_input.setText(self.user_info.password)
        self.first_name_input.setText(self.user_info.first_name)
        self.last_name_input.setText(self.user_info.last_name)
        self.gender_combo.setCurrentText(self.user_info.gender)
        self.birth_date_input.setText(self.user_info.birth_date)
        self.nationality_combo.setCurrentText(self.user_info.nationality)
        self.passport_number_input.setText(self.user_info.passport_number)
        self.passport_expiry_input.setText(self.user_info.passport_expiry)
        self.reference_input.setText(self.user_info.reference_number)
        
        # Load visa search settings
        self.visa_status_input.setText(self.user_info.visa_status)
        self.visa_location_input.setText(self.user_info.visa_location)
        self.visa_category_input.setText(self.user_info.visa_category)
        self.visa_type_input.setText(self.user_info.visa_type)
        self.check_visa_switch.setCurrentText(self.user_info.check_visa_switch)
        self.check_interval_input.setText(str(self.user_info.check_interval))
        self.wait_time_input.setText(str(self.user_info.wait_time))


def main():
    """Main application entry point"""
    app = QApplication(sys.argv)
    app.setApplicationName("Modern Visa Randevu Sistemi")
    app.setApplicationVersion("1.0")
    
    # Set application icon (optional)
    # app.setWindowIcon(QIcon("icon.ico"))
    
    window = ModernVisaBookingApp()
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()