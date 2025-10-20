# =============================================================================
# VFS Global Visa Appointment Automation Script
# Bu script VFS Global visa randevu sistemini otomatik olarak kontrol eder
# =============================================================================

# Standard library imports
import time
import asyncio
import tkinter as tk
from tkinter import simpledialog
import json
import os

# Selenium ve web automation imports
from seleniumbase import Driver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import ElementNotInteractableException

# Telegram bot integration
from telegram import Bot

# Optional mail OTP helpers (present in workspace)
# E-posta OTP kodlarını otomatik olarak almak için kullanılır

async def bilgilendirme(message):
    """
    Telegram bot üzerinden bildirim gönderir
    
    Args:
        message (str): Gönderilecek mesaj içeriği
    """
    # Telegram bot konfigürasyonu
    bot_token = "8016284721:AAE1pTh-n1InvD37rIfocdQZRpHuFBFlp4k"
    chat_ids = ["1145026697","1409999374"]
    
    
    # Bot oluştur ve mesaj gönder
    bot = Bot(token=bot_token)
    for chat_id in chat_ids:
        await bot.send_message(chat_id=chat_id, text=message)

#asyncio.run(mesaj()) 

#driver.switch_to.active_element.send_keys(Keys.ENTER) # Use this line to press Enter key if needed

try:
    from mail_control import get_mail, extract_otp_from_email
except Exception:
    get_mail = None
    extract_otp_from_email = None


def load_user_credentials():
    """
    user_credentials.json dosyasından kullanıcı bilgilerini yükler
    
    Returns:
        dict: Kullanıcı bilgileri ve ayarlar
    """
    try:
        with open('user_credentials.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Kullanıcı bilgileri yüklenirken hata: {e}")
        return None


def save_user_credentials(credentials):
    """
    Kullanıcı bilgilerini user_credentials.json dosyasına kaydeder
    """
    try:
        with open('user_credentials.json', 'w', encoding='utf-8') as f:
            json.dump(credentials, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print(f"Kullanıcı bilgileri kaydedilirken hata: {e}")
        return False


def deactivate_account_by_email(email):
    """
    Verilen e-posta adresine sahip hesabı aktiflikten çıkarır
    """
    data = load_user_credentials()
    if not data or 'accounts' not in data:
        return False
    updated = False
    for acc in data['accounts']:
        if acc.get('email') == email and acc.get('active', True):
            acc['active'] = False
            updated = True
            break
    if updated:
        return save_user_credentials(data)
    return False


def reactivate_all_accounts():
    """
    Tüm hesapları tekrar aktif eder
    """
    data = load_user_credentials()
    if not data or 'accounts' not in data:
        return False
    for acc in data['accounts']:
        acc['active'] = True
    return save_user_credentials(data)


def get_account_fail_count(email):
    """
    Verilen e-posta için user_credentials.json içindeki fail_count değerini döndürür
    (yoksa 0 kabul edilir)
    """
    data = load_user_credentials()
    if not data or 'accounts' not in data:
        return 0
    for acc in data['accounts']:
        if acc.get('email') == email:
            return int(acc.get('fail_count', 0))
    return 0


def set_account_fail_count(email, value):
    """
    Verilen e-posta için fail_count değerini ayarlar ve kaydeder
    """
    data = load_user_credentials()
    if not data or 'accounts' not in data:
        return False
    for acc in data['accounts']:
        if acc.get('email') == email:
            acc['fail_count'] = int(value)
            return save_user_credentials(data)
    return False


def increment_account_fail_count(email):
    """
    Verilen e-posta için fail_count değerini 1 arttırır ve yeni değeri döndürür
    """
    current = get_account_fail_count(email)
    new_value = current + 1
    print(new_value)
    set_account_fail_count(email, new_value)
    return new_value


def get_active_accounts(credentials):
    """
    Aktif hesapları filtreler
    
    Args:
        credentials (dict): Kullanıcı bilgileri
        
    Returns:
        list: Aktif hesaplar listesi
    """
    if not credentials or 'accounts' not in credentials:
        return []
    
    return [account for account in credentials['accounts'] if account.get('active', False)]


# Hesap deneme sırasını çevirmek için global indeks
rotation_index = 0

def get_rotated_accounts(accounts):
    """
    Global döngü indeksine göre hesap listesini döndürür.
    Aynı mail, tüm mailler denenmeden tekrar denenmez.
    """
    if not accounts:
        return []
    idx = rotation_index % len(accounts)
    return accounts[idx:] + accounts[:idx]


def attempt_login_with_account(account, driver, wait):
    """
    Belirli bir hesap ile login denemesi yapar
    
    Args:
        account (dict): Hesap bilgileri
        driver: Selenium driver
        wait: WebDriverWait objesi
        
    Returns:
        bool: Login başarılı ise True, aksi halde False
    """
    try:
        print(f"🔐 {account['description']} ({account['email']}) ile login deneniyor...")
        
        # Email ve password input alanlarını bul
        email_input = wait.until(EC.presence_of_element_located((By.ID, "email")))
        password_input = wait.until(EC.presence_of_element_located((By.ID, "password")))
        
        # Input alanlarını temizle ve değerleri gir
        email_input.clear()
        email_input.send_keys(account['email'])
        password_input.clear()
        password_input.send_keys(account['password'])
        print(f"✅ {account['email']} bilgileri girildi")
        
        time.sleep(1)
        
        # Login butonuna tıkla
        login_btn = wait.until(
            EC.element_to_be_clickable((By.XPATH, "//*[@class='mdc-button__label' and contains(text(), 'Oturum Aç')]"))
        )
        login_btn.click()
        print(f"✅ Login butonuna tıklandı - {account['email']}")
        
        time.sleep(8)  # Login işlemi sonrası bekle
        
        # Captcha kontrolü (login sonrası)
        try:
            driver.uc_gui_click_captcha()
        except Exception:
            pass
            
        # OTP kontrolü - eğer OTP sayfasındaysak login başarılı
        try:
            otp_input = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "input[placeholder='**********']")))
            print(f"✅ {account['email']} ile login başarılı - OTP sayfasına yönlendirildi")
            return True
        except Exception:
            # OTP sayfası değilse, hata mesajı kontrol et
            try:
                error_elements = driver.find_elements(By.CLASS_NAME, "alert")
                if error_elements:
                    error_text = error_elements[0].text
                    print(f"❌ {account['email']} ile login başarısız: {error_text}")
                else:
                    print(f"❌ {account['email']} ile login başarısız - Bilinmeyen hata")
                    # Bilinmeyen hata durumunda maili pasif yap
                    try:
                        if deactivate_account_by_email(account['email']):
                            print(f"❗ {account['email']} aktiflikten çıkarıldı (bilinmeyen hata)")
                    except Exception:
                        pass
            except Exception:
                print(f"❌ {account['email']} ile login başarısız - Hata tespit edilemedi")
            return False
            
    except Exception as e:
        print(f"❌ {account['email']} ile login sırasında hata: {e}")
        return False


def get_input_dialog(title, prompt):
    """
    Kullanıcıdan input almak için GUI dialog açar
    
    Args:
        title (str): Dialog başlığı
        prompt (str): Kullanıcıya gösterilecek mesaj
        
    Returns:
        str: Kullanıcının girdiği değer
    """
    # Tkinter root window oluştur ve gizle
    root = tk.Tk()
    root.withdraw()
    
    # Input dialog göster
    user_input = simpledialog.askstring(title, prompt)
    root.destroy()
    
    return user_input

def handle_cloudflare_dialog():
    """
    Cloudflare captcha dialog'unu tespit eder ve işler
    
    Returns:
        bool: Dialog başarıyla işlendiyse True, aksi halde False
    """
    try:
        # Cloudflare captcha dialog'unu tespit et
        dialog_title = wait.until(EC.presence_of_element_located(
            (By.XPATH, "//div[contains(@class, 'mat-mdc-dialog-title') and contains(text(), 'Captcha')]")
        ))
        print("Cloudflare captcha dialog'u tespit edildi!")
        
        # Captcha çözümü için bekle
        time.sleep(8)
        
        # Captcha'yı otomatik olarak çözmeye çalış
        try:
            driver.uc_gui_click_captcha()
        except Exception:
            pass
        
        time.sleep(1)
        
        # Submit butonunu bul ve tıkla
        submit_button = wait.until(EC.element_to_be_clickable(
            (By.XPATH, "//button[contains(@class, 'mat-mdc-raised-button')]//span[contains(text(), 'Submit')]")
        ))
        submit_button.click()
        print("Submit butonuna tıklandı")
        
        time.sleep(2)
        return True
        
    except Exception as e:
        print(f"Cloudflare dialog işlemi başarısız: {e}")
        return False


# =============================================================================
# WEB DRIVER KONFIGÜRASYONU
# =============================================================================

# SeleniumBase driver oluştur (undetected Chrome kullanarak)
driver = Driver(uc=True, headless=False)
wait = WebDriverWait(driver, 8)

# VFS Global login sayfası URL'i
url = "https://visa.vfsglobal.com/tur/tr/fra/login"

# Sayfayı aç ve bağlantı sorunları için yeniden bağlan
driver.uc_open_with_reconnect(url, reconnect_time=6)

def main():
    """
    Ana otomasyon fonksiyonu - VFS Global login ve randevu kontrol süreci
    """
    print(f"Mevcut URL: {driver.current_url}")
    
    # Dashboard kontrolü - eğer dashboard'da değilsek login sayfasına git
    if "dashboard" not in driver.current_url and "login" not in driver.current_url:
        print("🔄 Dashboard'da değil, login sayfasına yönlendiriliyor...")
        print(f"📍 Mevcut sayfa: {driver.current_url}")
        driver.get(url)
        time.sleep(3)
        
        # Cookie onayını reddet (varsa)
        try:
            cookie_reject = wait.until(EC.presence_of_element_located((By.ID, "onetrust-reject-all-handler")))
            time.sleep(1)
            cookie_reject.click()
            print("Cookie onayı reddedildi")
        except Exception:
            pass
        
        time.sleep(1)
        # Cloudflare/Turnstile captcha kontrolü
        try:
            driver.uc_gui_click_captcha()
        except Exception:
            pass
    
    # Login sayfasında mı kontrol et
    if "login" in driver.current_url:
        
        new_fail = 0
        # =============================================================================
        # LOGIN SAYFASI İŞLEMLERİ
        # =============================================================================
        time.sleep(6)  # Sayfa yüklenmesi için bekle

        # Cookie onayını reddet (varsa)
        try:
            cookie_reject = wait.until(EC.presence_of_element_located((By.ID, "onetrust-reject-all-handler")))
            time.sleep(1)
            cookie_reject.click()
            print("Cookie onayı reddedildi")
        except Exception:
            pass
        
        time.sleep(1)
        # Cloudflare/Turnstile captcha kontrolü
        try:
            driver.uc_gui_click_captcha()
        except Exception:
            pass
        # =============================================================================
        # ÇOKLU HESAP LOGIN DENEMESİ
        # =============================================================================
        
        # Kullanıcı bilgilerini yükle
        credentials = load_user_credentials()
        if not credentials:
            print("❌ Kullanıcı bilgileri yüklenemedi, varsayılan hesap kullanılıyor")
            # Varsayılan hesap bilgileri
            exit()
        
        else:
            active_accounts = get_active_accounts(credentials)
            print(active_accounts)
            if not active_accounts:
                print("❌ Aktif hesap bulunamadı, varsayılan hesap kullanılıyor")
                exit()
        
        print(f"📋 {len(active_accounts)} aktif hesap bulundu")
        
        # Her hesap ile login denemesi (rotasyonlu sıra) - başarısızsa tek denemede pasife al
        login_successful = False
        successful_account = None

        accounts_to_try = get_rotated_accounts(active_accounts)
        for i, account in enumerate(accounts_to_try):
            print(f"\n🔄 Hesap {i+1}/{len(accounts_to_try)} deneniyor...")

            try:
                # Sayfayı tazeleyip tek deneme yap
                if i > 0:
                    print("🔄 Login sayfası yeniden açılıyor...")
                    driver.get(url)
                    time.sleep(3)

                    # Cookie onayını reddet (varsa)
                    try:
                        cookie_reject = wait.until(EC.presence_of_element_located((By.ID, "onetrust-reject-all-handler")))
                        time.sleep(1)
                        cookie_reject.click()
                        print("Cookie onayı reddedildi")
                    except Exception:
                        pass

                    time.sleep(1)
                    # Cloudflare/Turnstile captcha kontrolü
                    try:
                        driver.uc_gui_click_captcha()
                    except Exception:
                        pass

                print(f"🧪 {account['email']} için tek deneme başlıyor")
                if attempt_login_with_account(account, driver, wait):
                    login_successful = True
                    successful_account = account
                    print(f"✅ {account['email']} ile login başarılı!")
                    break
                else:
                    print(f"❌ {account['email']} ile login başarısız - hesap pasife alınacak")
                    try:
                        if deactivate_account_by_email(account['email']):
                            print(f"❗ {account['email']} aktiflikten çıkarıldı")
                    except Exception:
                        pass

                # Kalan aktif hesap var mı kontrol et; yoksa hepsini yeniden aktif et ve turu yeniden başlat
                latest = load_user_credentials()
                remaining_active = get_active_accounts(latest) if latest else []
                if not remaining_active:
                    print("🔁 Tüm mailler pasif; hepsi yeniden aktif ediliyor ve döngü baştan başlayacak")
                    if reactivate_all_accounts():
                        print("✅ Tüm mailler yeniden aktif edildi")
                    return

            except Exception as e:
                print(f"❌ {account['email']} ile login sırasında beklenmeyen hata: {e}")
                if credentials and credentials.get('settings', {}).get('error_screenshot', True):
                    driver.save_screenshot(f"login_error_{account['email'].replace('@', '_at_')}.png")
                continue
        
        # Hiçbir hesap ile login başarısızsa
        if not login_successful:
            print("❌ Tüm hesaplar ile login başarısız!")
            driver.save_screenshot("all_login_failed.png")
            asyncio.run(bilgilendirme("❌ Tüm hesaplar ile login başarısız!"))
            raise Exception("Tüm hesaplar ile login başarısız")
        
        print(f"🎉 Başarılı login: {successful_account['email']}")
        asyncio.run(bilgilendirme(f"✅ Login başarılı: {successful_account['email']}"))
            
        # =============================================================================
        # OTP (ONE-TIME PASSWORD) İŞLEMLERİ
        # =============================================================================
        
        try:
            # OTP input alanını bul
            otp_input = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "input[placeholder='**********']")))
            
            otp_code = None
            
            # E-posta OTP'sini otomatik olarak almaya çalış (2 deneme)
            if get_mail and extract_otp_from_email:
                try:
                    otp_code = extract_otp_from_email(
                        get_mail(username="burakcaann5@gmail.com", password="fgvp jlxe btrl ekqg", imap_server="imap.gmail.com")
                    )
                    if otp_code:
                        print(f"✅ OTP kodu e-postadan alındı ({successful_account['email']})")
                except Exception:
                    otp_code = None
                    print(f"❌ E-postadan OTP alınamadı (ilk deneme) ({successful_account['email']})")
                
                if not otp_code:
                    time.sleep(12)
                    try:
                        otp_code = extract_otp_from_email(
                            get_mail(username="burakcaann5@gmail.com", password="fgvp jlxe btrl ekqg", imap_server="imap.gmail.com")
                        )
                        if otp_code:
                            print(f"✅ OTP kodu e-postadan alındı (2. deneme) ({successful_account['email']})")
                    except Exception:
                        otp_code = None
                        print(f"❌ E-postadan OTP alınamadı (2. deneme) ({successful_account['email']})")

            # Hâlâ yoksa hesabı pasif yap ve döngüyü bitir
            if not otp_code:
                try:
                    if deactivate_account_by_email(successful_account['email']):
                        print(f"❗ {successful_account['email']} aktiflikten çıkarıldı (OTP gelmedi)")
                except Exception:
                    pass
                latest = load_user_credentials()
                remaining_active = get_active_accounts(latest) if latest else []
                if not remaining_active:
                    print("🔁 Tüm mailler pasifti; hepsi yeniden aktif ediliyor")
                    if reactivate_all_accounts():
                        print("✅ Tüm mailler yeniden aktif edildi")
                return
            
            # OTP kodunu gir
            otp_input.send_keys(otp_code)
            time.sleep(2)
            
            # OTP submit butonuna tıkla
            submit_otp = wait.until(EC.element_to_be_clickable((By.CLASS_NAME, "mdc-button__label")))
            submit_otp.click()
            print(f"✅ OTP kodu gönderildi ({successful_account['email']})")
            
        except Exception as e:
            print(f"❌ OTP işlemi başarısız: {e}")
            pass
    
    elif "dashboard" not in driver.current_url:
        print("❌ Dashboard sayfasına erişilemedi - Mail geçici ban yemiş olabilir")
        print("🔄 Login sayfasına geri dönülüyor ve diğer hesap deneniyor...")
        asyncio.run(bilgilendirme("❌ Dashboard erişilemedi - Mail ban kontrolü yapılıyor"))
        
        # Login sayfasına geri dön
        try:
            driver.get(url)
            time.sleep(3)
            
            # Cookie onayını reddet (varsa)
            try:
                cookie_reject = wait.until(EC.presence_of_element_located((By.ID, "onetrust-reject-all-handler")))
                time.sleep(1)
                cookie_reject.click()
                print("Cookie onayı reddedildi")
            except Exception:
                pass
            
            time.sleep(1)
            # Cloudflare/Turnstile captcha kontrolü
            try:
                driver.uc_gui_click_captcha()
            except Exception:
                pass
            
            # Kullanıcı bilgilerini tekrar yükle
            credentials = load_user_credentials()
            if not credentials:
                print("❌ Kullanıcı bilgileri yüklenemedi, varsayılan hesap kullanılıyor")
                default_account = {
                    "email": "yunusemretom@gmail.com",
                    "password": "78Yunus3!",
                    "description": "Varsayılan hesap"
                }
                active_accounts = [default_account]
            else:
                active_accounts = get_active_accounts(credentials)
                if not active_accounts:
                    print("❌ Aktif hesap bulunamadı, varsayılan hesap kullanılıyor")
                    default_account = {
                        "email": "yunusemretom@gmail.com", 
                        "password": "78Yunus3!",
                        "description": "Varsayılan hesap"
                    }
                    active_accounts = [default_account]
            
            print(f"📋 {len(active_accounts)} aktif hesap ile yeniden deneme yapılıyor")
            
            # Her hesap ile login denemesi (rotasyonlu sıra) - başarısızsa tek denemede pasife al
            login_successful = False
            successful_account = None

            accounts_to_try = get_rotated_accounts(active_accounts)
            for i, account in enumerate(accounts_to_try):
                print(f"\n🔄 Hesap {i+1}/{len(accounts_to_try)} deneniyor...")

                try:
                    # Sayfayı tazeleyip tek deneme yap
                    if i > 0:
                        print("🔄 Login sayfası yeniden açılıyor...")
                        driver.get(url)
                        time.sleep(3)

                        # Cookie onayını reddet (varsa)
                        try:
                            cookie_reject = wait.until(EC.presence_of_element_located((By.ID, "onetrust-reject-all-handler")))
                            time.sleep(1)
                            cookie_reject.click()
                            print("Cookie onayı reddedildi")
                        except Exception:
                            pass

                        time.sleep(1)
                        # Cloudflare/Turnstile captcha kontrolü
                        try:
                            driver.uc_gui_click_captcha()
                        except Exception:
                            pass

                    print(f"🧪 {account['email']} için tek deneme başlıyor")
                    if attempt_login_with_account(account, driver, wait):
                        login_successful = True
                        successful_account = account
                        print(f"✅ {account['email']} ile login başarılı!")
                        break
                    else:
                        print(f"❌ {account['email']} ile login başarısız - hesap pasife alınacak")
                        try:
                            if deactivate_account_by_email(account['email']):
                                print(f"❗ {account['email']} aktiflikten çıkarıldı")
                        except Exception:
                            pass

                    # Kalan aktif hesap var mı kontrol et; yoksa hepsini yeniden aktif et ve turu yeniden başlat
                    latest = load_user_credentials()
                    remaining_active = get_active_accounts(latest) if latest else []
                    if not remaining_active:
                        print("🔁 Tüm mailler pasif; hepsi yeniden aktif ediliyor ve döngü baştan başlayacak")
                        if reactivate_all_accounts():
                            print("✅ Tüm mailler yeniden aktif edildi")
                        return

                except Exception as e:
                    print(f"❌ {account['email']} ile login sırasında beklenmeyen hata: {e}")
                    if credentials and credentials.get('settings', {}).get('error_screenshot', True):
                        driver.save_screenshot(f"login_error_{account['email'].replace('@', '_at_')}.png")
                    continue
            
            # Hiçbir hesap ile login başarısızsa
            if not login_successful:
                print("❌ Tüm hesaplar ile login başarısız!")
                driver.save_screenshot("all_login_failed.png")
                asyncio.run(bilgilendirme("❌ Tüm hesaplar ile login başarısız!"))  
                raise Exception("Tüm hesaplar ile login başarısız")
            
            print(f"🎉 Başarılı login: {successful_account['email']}")
            asyncio.run(bilgilendirme(f"✅ Login başarılı: {successful_account['email']}"))
            
            # OTP işlemleri
            try:
                # OTP input alanını bul
                otp_input = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "input[placeholder='**********']")))
                
                otp_code = None
                
                # E-posta OTP'sini otomatik olarak almaya çalış (2 deneme)
                if get_mail and extract_otp_from_email:
                    try:
                        otp_code = extract_otp_from_email(
                            get_mail(username="yunusemretom@gmail.com", password="hrua lyrh orka qlvt", imap_server="imap.gmail.com")
                        )
                        if otp_code:
                            print(f"✅ OTP kodu e-postadan alındı ({successful_account['email']})")
                    except Exception:
                        otp_code = None
                        print(f"❌ E-postadan OTP alınamadı (ilk deneme) ({successful_account['email']})")
                    
                    if not otp_code:
                        time.sleep(12)
                        try:
                            otp_code = extract_otp_from_email(
                                get_mail(username="yunusemretom@gmail.com", password="hrua lyrh orka qlvt", imap_server="imap.gmail.com")
                            )
                            if otp_code:
                                print(f"✅ OTP kodu e-postadan alındı (2. deneme) ({successful_account['email']})")
                        except Exception:
                            otp_code = None
                            print(f"❌ E-postadan OTP alınamadı (2. deneme) ({successful_account['email']})")

                # Hâlâ yoksa hesabı pasif yap ve döngüyü bitir
                if not otp_code:
                    try:
                        if deactivate_account_by_email(successful_account['email']):
                            print(f"❗ {successful_account['email']} aktiflikten çıkarıldı (OTP gelmedi)")
                    except Exception:
                        pass
                    latest = load_user_credentials()
                    remaining_active = get_active_accounts(latest) if latest else []
                    if not remaining_active:
                        print("🔁 Tüm mailler pasifti; hepsi yeniden aktif ediliyor")
                        if reactivate_all_accounts():
                            print("✅ Tüm mailler yeniden aktif edildi")
                    return
                
                # OTP kodunu gir
                otp_input.send_keys(otp_code)
                time.sleep(2)
                
                # OTP submit butonuna tıkla
                submit_otp = wait.until(EC.element_to_be_clickable((By.CLASS_NAME, "mdc-button__label")))
                submit_otp.click()
                print(f"✅ OTP kodu gönderildi ({successful_account['email']})")
                
            except Exception as e:
                print(f"❌ OTP işlemi başarısız: {e}")
                pass
                
        except Exception as e:
            print(f"❌ Dashboard kontrolü sırasında hata: {e}")
            asyncio.run(bilgilendirme(f"❌ Dashboard kontrolü sırasında hata: {str(e)}"))
            raise e
    
    time.sleep(6)  # Login işlemi sonrası bekleme
    
    if "page-not-found" in driver.current_url:
        print("mail aktif değil diğer maile geç")
        # Mevcut başarılı hesap varsa onu pasif yap, yoksa son deneneni pasif yap
        try:
            current_email = successful_account['email'] if 'successful_account' in locals() and successful_account else None
        except Exception:
            current_email = None
        if not current_email:
            # İlk rotasyon listesindeki sıradaki hesabı tahmini olarak pasif yapma fallback'i
            try:
                current_email = accounts_to_try[i]['email']  # mevcut döngü kapsamı
            except Exception:
                current_email = None
        if current_email:
            deactivated = deactivate_account_by_email(current_email)
            if deactivated:
                print(f"❗ {current_email} aktiflikten çıkarıldı")
            else:
                print(f"⚠️ {current_email} aktiflikten çıkarılamadı")
        
        # Aktif hesap kaldı mı kontrol et; yoksa hepsini tekrar aktif et
        latest = load_user_credentials()
        remaining_active = get_active_accounts(latest) if latest else []
        if not remaining_active:
            print("🔁 Tüm mailler pasifti; hepsi yeniden aktif ediliyor")
            if reactivate_all_accounts():
                print("✅ Tüm mailler yeniden aktif edildi")
            else:
                print("⚠️ Mailler yeniden aktif edilemedi")
        
        # Bu döngüyü bitir ve bir sonrakinde rotasyon ilerlesin
        return
    # =============================================================================
    # YENİ REZERVASYON BAŞLATMA
    # =============================================================================
    
    try:
        # "Yeni Rezervasyon Başlat" butonunu bul ve tıkla (2 kez deneme)
        for attempt in range(2):
            buttons = wait.until(
                EC.presence_of_all_elements_located(
                    (By.XPATH, "//*[@class='mdc-button__label' and contains(text(), 'Yeni Rezervasyon Başlat')]")
                )
            )
            
            if buttons:
                buttons[-1].click()  # Son butonu tıkla
                time.sleep(2)
                print(f"Yeni Rezervasyon Başlat butonuna tıklandı (deneme {attempt + 1})")
                break
                
    except ElementNotInteractableException:
        # Element bulundu ama tıklanamıyor, yine de tıklamaya çalış
        try:
            buttons[0].click()
            print("Yeni Rezervasyon Başlat butonuna tıklandı (alternatif yöntem)")
        except:
            pass

    except Exception as e:
        print(f"Yeni Rezervasyon Başlat butonları bulunamadı veya tıklanamadı. Hata: {e}")
        try:
            buttons[0].click()
        except:
            print("Rezervasyon başlatılamadı")
            return

    print("Yeni Rezervasyon Başlatıldı.")
    time.sleep(3)

    # =============================================================================
    # REZERVASYON FORMU SEÇİMLERİ
    # =============================================================================
    
    # Uygulama merkezi seçimi (İstanbul)
    print("Uygulama merkezi seçiliyor...")
    for i in range(2):
        try:
            center_select = wait.until(
                EC.element_to_be_clickable((By.XPATH, "//span[normalize-space(text())='Uygulama merkezinizi Seçiniz']"))
            )
            center_select.click()
            print("Merkez seçim dropdown'u açıldı")
            break
        except Exception as e:
            print(f"Merkez seçiminde hata, {i+1}. deneme: {e}")
            if i == 1:
                raise

    # İstanbul seçeneğini seç
    print("İstanbul seçeneği seçiliyor...")
    for i in range(2):
        try:
            istanbul_option = wait.until(EC.element_to_be_clickable((By.XPATH, "//*[@id='IBY']")))
            istanbul_option.click()
            time.sleep(2)
            print("İstanbul seçildi")
            break
        except Exception as e:
            print(f"İstanbul seçeneğinde hata, {i+1}. deneme: {e}")
            if i == 1:
                raise

    # Başvuru kategorisi seçimi (SSV - Schengen Short Stay Visa)
    print("Başvuru kategorisi seçiliyor...")
    for i in range(2):
        try:        
            category_select = wait.until(
                EC.element_to_be_clickable((By.XPATH, "//span[normalize-space(text())='Başvuru Kategorinizi Seçiniz']"))
            )
            category_select.click()
            print("Kategori seçim dropdown'u açıldı")
            
            ssv_option = wait.until(EC.element_to_be_clickable((By.XPATH, "//*[@id='SSV']")))
            ssv_option.click()
            time.sleep(2)
            print("SSV (Schengen Short Stay Visa) seçildi")
            break
        except Exception as e:
            print(f"Kategori seçiminde hata, {i+1}. deneme: {e}")
            if i == 1:
                raise

    # Cloudflare dialog kontrolü
    print("Cloudflare dialog kontrolü yapılıyor...")
    handle_cloudflare_dialog()

    # İkinci kategori seçimi (opsiyonel - Short Stay)
    print("İkinci kategori seçimi kontrol ediliyor...")
    try:
        category_select = wait.until(
            EC.element_to_be_clickable((By.XPATH, "//span[normalize-space(text())='Başvuru Kategorinizi Seçiniz']"))
        )
        category_select.click()
        short_stay_option = wait.until(EC.element_to_be_clickable((By.XPATH, "//*[@id='SHORSTD']")))
        short_stay_option.click()
        time.sleep(2)
        print("Short Stay kategorisi seçildi")
    except Exception:
        print("İkinci kategori seçimi bulunamadı (normal)")
        pass

    # =============================================================================
    # RANDEVU DURUMU KONTROLÜ

    
    # =============================================================================
    
    print("Randevu durumu kontrol ediliyor...")
    try:
        # Alert mesajını bul ve oku
        mesaj = wait.until(EC.element_to_be_clickable((By.CLASS_NAME, "alert"))).text
        
        if "Üzgünüz" in mesaj:
            print("❌ Randevu bulunamadı.")
            # Telegram bildirimi gönder
            asyncio.run(bilgilendirme("❌ Randevu bulunamadı."))
            # Başarılı giriş yapılan hesabı bul ve fail counter'ı arttır

            try:
                current_email = successful_account['email'] if 'successful_account' in locals() and successful_account else None
            except Exception:
                current_email = None
            # Fallback: döngü kapsamındaki son denenmiş hesabın e-postası
            if not current_email:
                try:
                    current_email = accounts_to_try[i]['email']
                except Exception:
                    current_email = None

            if current_email:
                new_fail = increment_account_fail_count(current_email)
                print(f"⚠️ {current_email} için randevu bulunamadı sayaçı: {new_fail}")
                # 5'e ulaştıysa hesabı pasif yap ve bildir
                if new_fail >= 5:
                    if deactivate_account_by_email(current_email):
                        print(f"❗ {current_email} 5 kez randevu bulunamadığı için pasife alındı")
                        asyncio.run(bilgilendirme(f"❗ {current_email} 5 kez randevu bulunamadığı için pasife alındı. Diğer hesaba geçiliyor."))
                        driver.get("https://visa.vfsglobal.com/tur/tr/fra/login")
                    else:
                        print(f"⚠️ {current_email} pasife alınamadı")
            else:
                print("⚠️ Geçerli hesap e-postası bulunamadı; sayaç artırılamadı")
        else:
            print(f"✅ Randevu bulundu: {mesaj}")
            # Telegram bildirimi gönder
            asyncio.run(bilgilendirme(f"""🟢 Fransa | Tourism - Short Term Standard | Istanbul

                                        📍 Merkez: Istanbul
                                        🎯 Ülke: Fransa
                                        📄 Kategori: Tourism - Short Term Standard
                                        📅 Slotlar: {mesaj}"""))
            # Randevu bulunduğunda sayaç sıfırlanır
            try:
                current_email = successful_account['email'] if 'successful_account' in locals() and successful_account else None
            except Exception:
                current_email = None
            if current_email:
                set_account_fail_count(current_email, 0)
                print(f"🔄 {current_email} için randevu başarısında sayaç sıfırlandı")
            
    except Exception as e:
        print(f"Randevu durumu kontrol edilemedi: {e}")

    # =============================================================================
    # ANA SAYFAYA DÖNÜŞ
    # =============================================================================
    
    print("Ana sayfaya dönülüyor...")
    try:
        # VFS Global logosuna tıklayarak ana sayfaya dön
        logo_anchor = wait.until(
            EC.element_to_be_clickable((By.XPATH, "//img[@alt='VFS.Global logo']/ancestor::a[1]"))
        )
        logo_anchor.click()
        print("Ana sayfaya dönüldü")
    except Exception as e:
        print(f"Ana sayfaya dönülemedi: {e}")
        pass

# =============================================================================
# ANA PROGRAM ÇALIŞTIRMA
# =============================================================================

# Script 10 kez çalıştırılır (sürekli randevu kontrolü için)
print("🚀 VFS Global Randevu Kontrol Scripti Başlatılıyor...")
print("📋 Script 10 kez çalışacak ve her seferinde randevu durumunu kontrol edecek")
print("🔐 Çoklu hesap desteği aktif - hata durumunda otomatik hesap değiştirme")
print("=" * 60)

# Kullanıcı bilgilerini önceden yükle
credentials = load_user_credentials()
if credentials:
    active_accounts = get_active_accounts(credentials)
    print(f"📋 {len(active_accounts)} aktif hesap yüklendi:")
    for account in active_accounts:
        print(f"   • {account['description']} ({account['email']})")
else:
    print("⚠️ Kullanıcı bilgileri yüklenemedi, varsayılan hesap kullanılacak")

print("=" * 60)
i = 0
while True:
    i += 1
    print(f"\n🔄 Döngü {i} başlatılıyor...")
    try:
        main()
        print(f"✅ Döngü {i} tamamlandı")
        # Bir sonraki döngüde ilk denenecek hesabı ilerlet
        if 'active_accounts' in globals() and active_accounts:
            rotation_index = (rotation_index + 1) % len(active_accounts)
        
    except Exception as e:
        print(f"❌ Döngü {i} sırasında hata: {e}")
        # Hata durumunda Telegram bildirimi
        try:
            asyncio.run(bilgilendirme(f"❌ Döngü {i} sırasında hata: {str(e)}"))
        except Exception:
            pass
    
    print("⏳ Sonraki döngü için 30 saniye bekleniyor...")
    time.sleep(30)
    

print("\n🏁 Tüm döngüler tamamlandı!")
print("📱 Telegram bildirimleri kontrol edin")


