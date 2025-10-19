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
    chat_id = "1145026697"
    
    # Bot oluştur ve mesaj gönder
    bot = Bot(token=bot_token)
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
        
        print(f"📋 {len(active_accounts)} aktif hesap bulundu")
        
        # Her hesap ile login denemesi
        login_successful = False
        successful_account = None
        
        for i, account in enumerate(active_accounts):
            print(f"\n🔄 Hesap {i+1}/{len(active_accounts)} deneniyor...")
            
            try:
                # Sayfayı yenile (önceki deneme varsa)
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
                
                # Login denemesi
                if attempt_login_with_account(account, driver, wait):
                    login_successful = True
                    successful_account = account
                    print(f"✅ {account['email']} ile login başarılı!")
                    break
                else:
                    print(f"❌ {account['email']} ile login başarısız")
                    
                    # Hesap değiştirme gecikmesi
                    if i < len(active_accounts) - 1:  # Son hesap değilse
                        delay = credentials.get('settings', {}).get('account_switch_delay', 5) if credentials else 5
                        print(f"⏳ Sonraki hesap için {delay} saniye bekleniyor...")
                        time.sleep(delay)
                        
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
            driver.quit()
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
            
            # E-posta OTP'sini otomatik olarak almaya çalış
            if get_mail and extract_otp_from_email:
                try:
                    otp_code = extract_otp_from_email(get_mail(username="burakcaann5@gmail.com",password="fgvp jlxe btrl ekqg",imap_server="imap.gmail.com"))
                    print(f"✅ OTP kodu e-postadan alındı ({successful_account['email']})")
                except Exception:
                    otp_code = None
                    print(f"❌ E-postadan OTP alınamadı ({successful_account['email']})")
            
            # Otomatik OTP alınamazsa kullanıcıdan iste
            if not otp_code:
                otp_code = get_input_dialog("Mail Kodu", f"Lütfen {successful_account['email']} için Mail kodunu girin: ")
                print(f"✅ OTP kodu kullanıcıdan alındı ({successful_account['email']})")
            
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
            
            # Her hesap ile login denemesi
            login_successful = False
            successful_account = None
            
            for i, account in enumerate(active_accounts):
                print(f"\n🔄 Hesap {i+1}/{len(active_accounts)} deneniyor...")
                
                try:
                    # Sayfayı yenile (önceki deneme varsa)
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
                    
                    # Login denemesi
                    if attempt_login_with_account(account, driver, wait):
                        login_successful = True
                        successful_account = account
                        print(f"✅ {account['email']} ile login başarılı!")
                        break
                    else:
                        print(f"❌ {account['email']} ile login başarısız")
                        
                        # Hesap değiştirme gecikmesi
                        if i < len(active_accounts) - 1:  # Son hesap değilse
                            delay = credentials.get('settings', {}).get('account_switch_delay', 5) if credentials else 5
                            print(f"⏳ Sonraki hesap için {delay} saniye bekleniyor...")
                            time.sleep(delay)
                            
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
                driver.quit()
                raise Exception("Tüm hesaplar ile login başarısız")
            
            print(f"🎉 Başarılı login: {successful_account['email']}")
            asyncio.run(bilgilendirme(f"✅ Login başarılı: {successful_account['email']}"))
            
            # OTP işlemleri
            try:
                # OTP input alanını bul
                otp_input = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "input[placeholder='**********']")))
                
                otp_code = None
                
                # E-posta OTP'sini otomatik olarak almaya çalış
                if get_mail and extract_otp_from_email:
                    try:
                        otp_code = extract_otp_from_email(get_mail(username="yunusemretom@gmail.com",password="hrua lyrh orka qlvt",imap_server="imap.gmail.com"))
                        print(f"✅ OTP kodu e-postadan alındı ({successful_account['email']})")
                    except Exception:
                        otp_code = None
                        print(f"❌ E-postadan OTP alınamadı ({successful_account['email']})")
                
                # Otomatik OTP alınamazsa kullanıcıdan iste
                if not otp_code:
                    otp_code = get_input_dialog("Mail Kodu", f"Lütfen {successful_account['email']} için Mail kodunu girin: ")
                    print(f"✅ OTP kodu kullanıcıdan alındı ({successful_account['email']})")
                
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
        else:
            print(f"✅ Randevu bulundu: {mesaj}")
            # Telegram bildirimi gönder
            asyncio.run(bilgilendirme(f"""🟢 Fransa | Tourism - Short Term Standard | Istanbul

                                        📍 Merkez: Istanbul
                                        🎯 Ülke: Fransa
                                        📄 Kategori: Tourism - Short Term Standard
                                        📅 Slotlar: {mesaj}"""))
            
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


