import undetected_chromedriver as uc
from webdriver_manager.chrome import ChromeDriverManager
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
from selenium_stealth import stealth
import pyautogui
import tkinter as tk
from tkinter import simpledialog
from mail_control import *


options = uc.ChromeOptions()
options.add_argument('--disable-blink-features=AutomationControlled')
options.add_argument("--profile-directory=Default")
options.add_argument("--user-data-dir=/var/tmp/chrome_user_data")
options.headless = False
driver = uc.Chrome(options=options)

driver.maximize_window()
wait = WebDriverWait(driver, 20)
driver.get("https://visa.vfsglobal.com/tur/tr/fra/login")
time.sleep(10)
# Cloudflare Turnstile elementini bul ve tıkla

def get_element_center(element):
    location = element.location
    size = element.size
    x = location['x'] + size['width'] // 2  
    y = location['y'] + size['height'] // 2
    return x, y


def get_input_dialog(title, prompt):
    root = tk.Tk()
    root.withdraw()  # Ana pencereyi gizle
    user_input = simpledialog.askstring(title, prompt)
    root.destroy()
    return user_input


def handle_cloudflare_dialog():
    """
    Cloudflare captcha dialog'unu tespit eder ve Enter tuşuna basar
    """
    try:
        # Cloudflare dialog'unu tespit et
        dialog_title = wait.until(EC.presence_of_element_located(
            (By.XPATH, "//div[contains(@class, 'mat-mdc-dialog-title') and contains(text(), 'Captcha')]")
        ))
        print("Cloudflare captcha dialog'u tespit edildi!")
        time.sleep(1)
        # Submit butonunu bul ve tıkla (Enter tuşu yerine)
        submit_button = wait.until(EC.element_to_be_clickable(
            (By.XPATH, "//button[contains(@class, 'mat-mdc-raised-button')]//span[contains(text(), 'Submit')]")
        ))
        submit_button.click()
        print("Submit butonuna tıklandı (Enter tuşu simülasyonu)")
        
        # Alternatif olarak Enter tuşu gönderme
        # pyautogui.press('enter')
        time.sleep(2)
        return True
        
    except Exception as e:
        print(f"Cloudflare dialog işlemi başarısız: {str(e)}")
        return False


def login():
    try:
        cerez = wait.until(EC.presence_of_element_located((By.ID, "onetrust-reject-all-handler")))
        time.sleep(2)
        cerez.click()
        time.sleep(1)
    except Exception as e:
        pass
    try:
        print("Turnstile elementi bulunuyor...")
        turnstile = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "app-cloudflare-captcha-container")))
        x, y = get_element_center(turnstile)
        print(x, y)
        pyautogui.click(x, y)
    except Exception as e:
        print("Turnstile elementi bulunamadı veya tıklanamadı:", str(e))
    username = wait.until(EC.presence_of_element_located((By.ID, "email")))
    # Kullanıcı adını al
    email="yunusemretom@gmail.com" # Buraya kendi emailinizi yazınız.
    username.send_keys(email)
    password = wait.until(EC.presence_of_element_located((By.ID, "password")))
    # Şifreyi al
    password_value="78Yunus3!" # Buraya kendi şifrenizi yazınız.
    password.send_keys(password_value)
    print("Kullanıcı adı ve şifre girildi.")
    time.sleep(5)
    try:
        driver.find_element("input", {"type":"checkbox"}).click()
    except Exception as e:
        pass
    time.sleep(1)   
    try:
        submit_button = wait.until(EC.element_to_be_clickable((By.XPATH, "//*[@class='mdc-button__label' and contains(text(), 'Oturum Aç')]")))
        submit_button.click()
    except:
        driver.refresh()
        time.sleep(2)
        login()

def main():
    if driver.current_url in "login":
        login()
        time.sleep(10)

        try:
            verification_code = extract_otp_from_email(get_mail())
            wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "input[placeholder='**********']"))).send_keys(verification_code)
        except Exception as e:
            print(e)
            verification_code = get_input_dialog("Mail Kodu", "Lütfen Mail kodunu girin: ")
            wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "input[placeholder='**********']"))).send_keys(verification_code)

        time.sleep(5)

        wait.until(EC.presence_of_element_located((By.CLASS_NAME, "mdc-button__label"))).click()
        time.sleep(4)


    try:
        for i in range(2):
            buttons = wait.until(
                EC.presence_of_all_elements_located((
                    By.XPATH, "//*[@class='mdc-button__label' and contains(text(), 'Yeni Rezervasyon Başlat')]"
                ))
            )
            print(f"Bulunan buton sayısı: {len(buttons)}")
            time.sleep(2)
            ActionChains(driver).move_to_element(buttons[-1]).click().perform()
    except:
        pass

            
    time.sleep(5)


    center_select = wait.until(EC.element_to_be_clickable((By.XPATH, "//span[normalize-space(text())='Uygulama merkezinizi Seçiniz']")))
    center_select.click()

    # 2. Açılan seçeneklerden bir tanesini seç
    # Örnek: İstanbul seçeneğini seçiyoruz
    istanbul_option = wait.until(EC.element_to_be_clickable(
        (By.XPATH, "//*[@id='IBY']")
    ))
    istanbul_option.click()
    time.sleep(5)

    center_select = wait.until(EC.element_to_be_clickable((By.XPATH, "//span[normalize-space(text())='Başvuru Kategorinizi Seçiniz']")))
    center_select.click()

    # 2. Açılan seçeneklerden bir tanesini seç
    # Örnek: İstanbul seçeneğini seçiyoruz
    istanbul_option = wait.until(EC.element_to_be_clickable(
        (By.XPATH, "//*[@id='SSV']")
    ))
    istanbul_option.click()
    time.sleep(5)

    try:
        center_select = wait.until(EC.element_to_be_clickable((By.XPATH, "//span[normalize-space(text())='Başvuru Kategorinizi Seçiniz']")))
        center_select.click()

        # 2. Açılan seçeneklerden bir tanesini seç
        # Örnek: İstanbul seçeneğini seçiyoruz
        istanbul_option = wait.until(EC.element_to_be_clickable(
            (By.XPATH, "//*[@id='SHORSTD']")
        ))
        istanbul_option.click()
        time.sleep(5)
    except Exception as e:
        pass

    mesaj = wait.until(EC.element_to_be_clickable((By.CLASS_NAME, "alert"))).text
    if "Üzgünüz" in mesaj:
        print("Randevu bulunamadı.")
        
    else:
        print("Randevu bulundu:", mesaj)


    # Click the VFS Global logo (anchor) via the image's alt text
    logo_anchor = wait.until(EC.element_to_be_clickable((By.XPATH, "//img[@alt='VFS.Global logo']/ancestor::a[1]")))
    logo_anchor.click()

    time.sleep(10)

if __name__ == "__main__":
    main()