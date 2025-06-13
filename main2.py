import undetected_chromedriver as uc
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException
import time
import tkinter as tk
from tkinter import simpledialog, messagebox
import logging

# Loglama ayarları
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- WebDriver Ayarları ---
def initialize_driver():
    options = uc.ChromeOptions()
    # Kullanıcı verilerini kaydetmek için, böylece her seferinde giriş yapmanız gerekmez
    options.add_argument("--user-data-dir=chrome-data")
    options.add_argument("--disable-blink-features=AutomationControlled") # Bot tespiti azaltma
    options.add_argument("--disable-extensions") # Uzantıları devre dışı bırak
    # Headless mod (tarayıcı arayüzünü göstermez) - Geliştirme aşamasında False tutulmalı
    options.headless = False 
    
    # Başlangıçta daha güvenli bir port kullanabiliriz
    options.add_argument("--remote-debugging-port=9222")

    try:
        driver = uc.Chrome(options=options)
        # selenium_stealth yerine uc kütüphanesinin kendi anti-detection özellikleri kullanılabilir.
        # Eğer stealth eklemek isterseniz:
        # from selenium_stealth import stealth
        # stealth(driver,
        #         languages=["en-US", "en"],
        #         vendor="Google Inc.",
        #         platform="Win32",
        #         webgl_vendor="Intel Inc.",
        #         renderer="Intel Iris OpenGL Engine",
        #         fix_hairline=True,
        #         )
        driver.maximize_window()
        logging.info("WebDriver başarıyla başlatıldı.")
        return driver
    except WebDriverException as e:
        logging.error(f"WebDriver başlatılırken hata oluştu: {e}")
        messagebox.showerror("Hata", "WebDriver başlatılamadı. Chrome tarayıcınızın güncel olduğundan emin olun.")
        exit()

# --- Yardımcı Fonksiyonlar ---
def get_input_dialog(title, prompt):
    """Kullanıcıdan GUI ile girdi almak için."""
    root = tk.Tk()
    root.withdraw()  # Ana pencereyi gizle
    user_input = simpledialog.askstring(title, prompt)
    root.destroy()
    return user_input

def handle_cookies(wait):
    """Çerez onayını reddetmek için."""
    try:
        logging.info("Çerez onayını reddetmeye çalışılıyor...")
        cerez = wait.until(EC.element_to_be_clickable((By.ID, "onetrust-reject-all-handler")))
        cerez.click()
        logging.info("Çerez onayı reddedildi.")
    except TimeoutException:
        logging.info("Çerez onayı elementi bulunamadı veya zaten işlenmiş.")
    except Exception as e:
        logging.warning(f"Çerez onayını reddederken hata oluştu: {e}")

def select_dropdown_option(wait, select_id, option_xpath):
    """
    Belirli bir mat-select dropdown'ından bir seçenek seçer.
    Args:
        wait: WebDriverWait nesnesi.
        select_id: mat-select elementinin ID'si (örneğin "mat-select-0").
        option_xpath: Seçilecek seçeneğin XPath'i (örneğin "//*[@id='IBY']").
    """
    try:
        dropdown = wait.until(EC.element_to_be_clickable((By.ID, select_id)))
        dropdown.click()
        logging.info(f"Dropdown '{select_id}' tıklandı.")
        
        option = wait.until(EC.element_to_be_clickable((By.XPATH, option_xpath)))
        option.click()
        logging.info(f"Seçenek '{option_xpath}' seçildi.")
        time.sleep(1) # Seçim sonrası sayfa dinamik olarak yüklenebilir
    except TimeoutException:
        logging.error(f"Dropdown '{select_id}' veya seçenek '{option_xpath}' bulunamadı/tıklanamadı. Sayfa yapısı değişmiş olabilir.")
        raise # Hatayı yukarı fırlat, ana akış durmalı
    except Exception as e:
        logging.error(f"Dropdown işlemi sırasında hata oluştu: {e}")
        raise

# --- Ana Otomasyon Akışı ---
def run_vfs_automation(email, password, ref_num, first_name, last_name, dob, passport_num, passport_exp):
    driver = initialize_driver()
    wait = WebDriverWait(driver, 30) # Daha uzun bir bekleme süresi

    try:
        driver.get("https://visa.vfsglobal.com/tur/tr/fra/login")
        handle_cookies(wait)
        
        # Cloudflare Turnstile'ı elle çözme uyarısı
        # Turnstile'ı otomatikleştirmek çok zordur. Bu, kullanıcı müdahalesi gerektirecektir.
        logging.warning("Cloudflare Turnstile doğrulamasını manuel olarak tamamlamanız gerekebilir.")
        messagebox.showinfo("Cloudflare Doğrulama", "Lütfen açılan tarayıcı penceresinde Cloudflare doğrulamasını (ben bir robot değilim) manuel olarak tamamlayın ve ardından Tamam'a tıklayın.")
        
        # Turnstile tamamlanana kadar bekleme (manuel müdahale sonrası)
        # Giriş elementlerinin görünür olmasını bekleyerek turnstile'ın geçildiğini anlarız.
        wait.until(EC.visibility_of_element_located((By.ID, "email")))
        logging.info("Cloudflare doğrulaması tamamlandı, giriş ekranı yüklendi.")

        # Giriş bilgileri
        username_field = wait.until(EC.presence_of_element_located((By.ID, "email")))
        username_field.send_keys(email)
        logging.info(f"E-posta girildi: {email}")

        password_field = wait.until(EC.presence_of_element_located((By.ID, "password")))
        password_field.send_keys(password)
        logging.info("Şifre girildi.")

        # "Beni Hatırla" veya benzeri checkbox
        try:
            remember_me_checkbox = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "input[type='checkbox']")))
            remember_me_checkbox.click()
            logging.info("Checkbox tıklandı.")
        except TimeoutException:
            logging.info("Checkbox bulunamadı veya tıklanamadı (opsiyonel).")
        except Exception as e:
            logging.warning(f"Checkbox tıklanırken hata: {e}")

        # Oturum Aç butonu
        submit_button = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[./span[@class='mdc-button__label' and contains(text(), 'Oturum Aç')]]")))
        submit_button.click()
        logging.info("Oturum Aç butonuna tıklandı.")
        
        # SMS Doğrulama
        sms_code = get_input_dialog("SMS Kodu", "Lütfen VFS Global'den gelen SMS kodunu girin:")
        sms_input = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "input[placeholder='**********']")))
        sms_input.send_keys(sms_code)
        logging.info("SMS kodu girildi.")
        
        verify_sms_button = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "button.mdc-button.mdc-button--raised")))
        verify_sms_button.click()
        logging.info("SMS Doğrula butonuna tıklandı.")
        
        # "Yeni Rezervasyon Başlat" veya "Devam Et" butonunu bulma (sayfaya göre değişebilir)
        # Önce başarılı giriş sonrası ilk butonu bekleyelim
        try:
            new_booking_button = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[./span[@class='mdc-button__label' and contains(text(), 'Yeni Rezervasyon Başlat')]]")))
            new_booking_button.click()
            logging.info("Yeni Rezervasyon Başlat butonuna tıklandı.")
        except TimeoutException:
            logging.warning("Yeni Rezervasyon Başlat butonu bulunamadı, mevcut rezervasyon akışına devam ediyor olabilir.")
            # Belki "Devam Et" butonu vardır, onu deneyelim
            try:
                continue_button_after_login = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[./span[@class='mdc-button__label' and contains(text(), 'Devam Et')]]")))
                continue_button_after_login.click()
                logging.info("Giriş sonrası Devam Et butonuna tıklandı.")
            except TimeoutException:
                logging.error("Giriş sonrası ne 'Yeni Rezervasyon Başlat' ne de 'Devam Et' butonu bulunamadı.")
                raise # Akışı durdur
        
        # --- Randevu Adımları ---
        logging.info("Randevu adımlarına başlanıyor...")

        # Başvuru Merkezi Seçimi (Örnek: İstanbul)
        select_dropdown_option(wait, "mat-select-0", "//*[@id='IBY']") # ID'nin 'IBY' olduğundan emin olun
        
        # Randevu Kategorisi Seçimi (Örnek: SSV - Standard Service Visa)
        select_dropdown_option(wait, "mat-select-4", "//*[@id='SSV']") # ID'nin 'SSV' olduğundan emin olun

        # Seyahat Süresi Seçimi (Örnek: SHORTSTD - Short Stay Standard)
        select_dropdown_option(wait, "mat-select-2", "//*[@id='SHORSTD']") # ID'nin 'SHORSTD' olduğundan emin olun
        
        # Randevu durumu kontrolü
        try:
            appointment_status_message = wait.until(EC.visibility_of_element_located((By.CLASS_NAME, "alert"))).text
            if "Üzgünüz" in appointment_status_message:
                logging.info("Randevu bulunamadı.")
                messagebox.showinfo("Randevu Durumu", "Üzgünüz, şu an için randevu bulunamadı.")
                return # Randevu yoksa burada bitir
            else:
                logging.info(f"Randevu bulundu: {appointment_status_message}")
                messagebox.showinfo("Randevu Durumu", f"Randevu bulundu: {appointment_status_message}\nLütfen tarayıcıyı kontrol edin.")
        except TimeoutException:
            logging.warning("Randevu durum mesajı elementi beklenenden farklı bir şekilde yüklendi veya bulunamadı.")
            # Belki direkt devam butonu görünürdür, devam edelim
        except Exception as e:
            logging.error(f"Randevu durumu kontrol edilirken hata: {e}")
            raise

        # Eğer randevu bulunursa veya mesaj yoksa devam et butonu
        continue_button_1 = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[./span[@class='mdc-button__label' and contains(text(), 'Devam Et')]]")))
        continue_button_1.click()
        logging.info("Randevu sonrası Devam Et butonuna tıklandı.")
        
        # --- Kişisel Bilgiler Formu ---
        logging.info("Kişisel bilgiler formu dolduruluyor...")
        try:
            ref_num_input = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "input[placeholder='Referans numaranızı giriniz']")))
            ref_num_input.send_keys(ref_num)
            logging.info(f"Referans numarası girildi: {ref_num}")
        except TimeoutException:
            logging.warning("Referans numarası alanı bulunamadı (belki opsiyonel).")

        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "input[placeholder='İsminizi Giriniz']"))).send_keys(first_name)
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "input[placeholder='Lütfen soy isminizi giriniz.']"))).send_keys(last_name)
        logging.info(f"Ad-Soyad girildi: {first_name} {last_name}")

        # Cinsiyet seçimi
        select_dropdown_option(wait, "(//mat-select)[1]", "//*[@class='mdc-list-item__primary-text' and contains(text(), 'Male')]") # 'Male' veya 'Female'
        
        wait.until(EC.presence_of_element_located((By.ID, "dateOfBirth"))).send_keys(dob)
        logging.info(f"Doğum tarihi girildi: {dob}")

        # Uyruk seçimi
        select_dropdown_option(wait, "(//mat-select)[2]", "//*[@class='mdc-list-item__primary-text' and contains(text(), 'Türkiye')]")
        
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "input[placeholder='pasaport Numarası Giriniz']"))).send_keys(passport_num)
        wait.until(EC.presence_of_element_located((By.ID, "passportExpirtyDate"))).send_keys(passport_exp)
        logging.info("Pasaport bilgileri girildi.")

        # Kaydet butonu
        save_button = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[./span[@class='mdc-button__label' and contains(text(), 'Kaydet')]]")))
        save_button.click()
        logging.info("Kişisel bilgiler kaydedildi.")
        
        # Sonraki "Devam Et" butonu
        continue_button_2 = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[./span[@class='mdc-button__label' and contains(text(), 'Devam Et')]]")))
        continue_button_2.click()
        logging.info("Kişisel bilgiler sonrası Devam Et butonuna tıklandı.")

        # Tek Seferlik Şifre (OTP) Oluştur
        otp_generate_button = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[./span[@class='mdc-button__label' and contains(text(), ' Tek Seferlik Şifre (OTP) Oluştur ')]]")))
        otp_generate_button.click()
        logging.info("OTP Oluştur butonuna tıklandı.")
        
        otp_code = get_input_dialog("OTP Kodu", "Lütfen VFS Global'den gelen OTP kodunu girin:")
        otp_input = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "input[placeholder='OTP']")))
        otp_input.send_keys(otp_code)
        logging.info("OTP kodu girildi.")

        otp_verify_button = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[./span[@class='mdc-button__label' and contains(text(), ' Doğrula ')]]")))
        otp_verify_button.click()
        logging.info("OTP Doğrula butonuna tıklandı.")
        
        # Devam Et
        continue_button_3 = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[./span[@class='mdc-button__label' and contains(text(), 'Devam Et')]]")))
        continue_button_3.click()
        logging.info("OTP sonrası Devam Et butonuna tıklandı.")
        
        # Randevu tarihi seçimi (İlk uygun tarihi tıkla)
        available_date = wait.until(EC.element_to_be_clickable((By.CLASS_NAME, "date-availiable")))
        available_date.click()
        logging.info("Uygun randevu tarihi seçildi.")

        # Zaman dilimi seçimi (Varsayılan olarak ilk radyo butonunu seçer)
        time_slot_radio = wait.until(EC.presence_of_element_located((By.ID, "STRadio1")))
        time_slot_radio.click()
        logging.info("Randevu zaman dilimi seçildi.")

        # Devam Et
        continue_button_4 = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[./span[@class='mdc-button__label' and contains(text(), 'Devam Et')]]")))
        continue_button_4.click()
        logging.info("Randevu zaman dilimi sonrası Devam Et butonuna tıklandı.")
        
        # Son Devam Et (Genellikle ödeme veya onay ekranı)
        final_continue_button = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[./span[@class='mdc-button__label' and contains(text(), 'Devam Et')]]")))
        final_continue_button.click()
        logging.info("Son Devam Et butonuna tıklandı. İşlem tamamlanmış olabilir.")

        messagebox.showinfo("Otomasyon Tamamlandı", "VFS Global randevu otomasyonu tamamlandı. Lütfen tarayıcıyı kontrol edin.")

    except TimeoutException as e:
        logging.error(f"Element beklenenden uzun süre bulunamadı: {e}")
        messagebox.showerror("Hata", f"Sayfada bir element bulunamadı veya yüklenmesi çok uzun sürdü. Kod akışı durduruldu. Detay: {e}")
    except NoSuchElementException as e:
        logging.error(f"Belirtilen element bulunamadı: {e}")
        messagebox.showerror("Hata", f"Beklenen bir element sayfada bulunamadı. Kod akışı durduruldu. Detay: {e}")
    except Exception as e:
        logging.error(f"Genel bir hata oluştu: {e}", exc_info=True)
        messagebox.showerror("Hata", f"Beklenmeyen bir hata oluştu. Kod akışı durduruldu. Detay: {e}")
    finally:
        # Tarayıcıyı açık tutmak için yorum satırına alabilirsiniz.
        # driver.quit() 
        logging.info("Otomasyon tamamlandı veya bir hata ile karşılaşıldı. Tarayıcı açık bırakıldı.")

# --- Kullanım ---
if __name__ == "__main__":
    # Bu bilgileri doğrudan koda yazmak yerine, güvenli bir şekilde dışarıdan alınması önerilir.
    # Örneğin, bir .env dosyası veya kullanıcıdan her seferinde GUI ile sormak.
    # Şimdilik örnek değerler:
    USER_EMAIL = "***@gmail.com" # Buraya kendi emailinizi yazınız.
    USER_PASSWORD = "********" # Buraya kendi şifrenizi yazınız.
    
    # Kişisel ve pasaport bilgileri
    USER_REF_NUM = "FRA1IS20257066125" # Başvuru Referans Numaranız
    USER_FIRST_NAME = "HALUK"
    USER_LAST_NAME = "KAYGA"
    USER_DOB = "24041975" # DDMMYYYY formatında
    USER_PASSPORT_NUM = "U34565375"
    USER_PASSPORT_EXP = "24042030" # DDMMYYYY formatında

    # Otomasyonu başlat
    run_vfs_automation(USER_EMAIL, USER_PASSWORD, USER_REF_NUM, USER_FIRST_NAME, USER_LAST_NAME, USER_DOB, USER_PASSPORT_NUM, USER_PASSPORT_EXP)