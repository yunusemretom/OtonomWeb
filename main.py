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

options = uc.ChromeOptions()
options.add_argument("--user-data-dir=chrome-data")
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
    email="***@gmail.com" # Buraya kendi emailinizi yazınız.

    username.send_keys(email)
    password = wait.until(EC.presence_of_element_located((By.ID, "password")))

    # Şifreyi al
    password_value="********" # Buraya kendi şifrenizi yazınız.


    password.send_keys(password_value)
    print("Kullanıcı adı ve şifre girildi.")

    time.sleep(2)
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

login()

sms = get_input_dialog("SMS Kodu", "Lütfen SMS kodunu girin: ")
wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "input[placeholder='**********']"))).send_keys(sms)
time.sleep(3)

wait.until(EC.presence_of_element_located((By.CLASS_NAME, "mdc-button__label"))).click()
time.sleep(4)

rezervasyon = wait.until(EC.element_to_be_clickable((By.XPATH, "//*[@class='mdc-button__label' and contains(text(), 'Yeni Rezervasyon Başlat')]")))
rezervasyon.click()
time.sleep(2)


center_select = wait.until(EC.element_to_be_clickable((By.ID, "mat-select-0")))
center_select.click()

# 2. Açılan seçeneklerden bir tanesini seç
# Örnek: İstanbul seçeneğini seçiyoruz
istanbul_option = wait.until(EC.element_to_be_clickable(
    (By.XPATH, "//*[@id='IBY']")
))
istanbul_option.click()
time.sleep(5)

center_select = wait.until(EC.element_to_be_clickable((By.ID, "mat-select-4")))
center_select.click()

# 2. Açılan seçeneklerden bir tanesini seç
# Örnek: İstanbul seçeneğini seçiyoruz
istanbul_option = wait.until(EC.element_to_be_clickable(
    (By.XPATH, "//*[@id='SSV']")
))
istanbul_option.click()
time.sleep(5)

center_select = wait.until(EC.element_to_be_clickable((By.ID, "mat-select-2")))
center_select.click()

# 2. Açılan seçeneklerden bir tanesini seç
# Örnek: İstanbul seçeneğini seçiyoruz
istanbul_option = wait.until(EC.element_to_be_clickable(
    (By.XPATH, "//*[@id='SHORSTD']")
))
istanbul_option.click()
time.sleep(5)

mesaj = wait.until(EC.element_to_be_clickable((By.CLASS_NAME, "alert"))).text
if "Üzgünüz" in mesaj:
    print("Randevu bulunamadı.")
    exit()
    
else:
    print("Randevu bulundu:", mesaj)
time.sleep(10)

wait.until(EC.element_to_be_clickable((By.XPATH, "//*[@class='mdc-button__label' and contains(text(), 'Devam Et')]"))).click()

time.sleep(2)
# Kişisel Bilgiler Formu
try:
    wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "input[placeholder='Referans numaranızı giriniz']"))).send_keys("FRA1IS20257066125")
except Exception as e:
    pass
time.sleep(2)
wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "input[placeholder='İsminizi Giriniz']"))).send_keys("HALUK")
wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "input[placeholder='Lütfen soy isminizi giriniz.']"))).send_keys("KAYGA")
time.sleep(2)
cinsiyet = wait.until(EC.element_to_be_clickable((By.XPATH, "(//mat-select)[1]")))
cinsiyet.click()
time.sleep(2)

# 2. Açılan seçeneklerden bir tanesini seç
# Örnek: İstanbul seçeneğini seçiyoruz
male = wait.until(EC.element_to_be_clickable(
    (By.XPATH, "//*[@class='mdc-list-item__primary-text' and contains(text(), 'Male')]")
))
male.click()
time.sleep(2)
wait.until(EC.element_to_be_clickable((By.ID, "dateOfBirth"))).send_keys("24041975")
time.sleep(2)
uyruk = wait.until(EC.element_to_be_clickable((By.XPATH, "(//mat-select)[2]")))
uyruk.click()
time.sleep(2)
# 2. Açılan seçeneklerden bir tanesini seç
# Örnek: İstanbul seçeneğini seçiyoruz
turk = wait.until(EC.element_to_be_clickable(
    (By.XPATH, "//*[@class='mdc-list-item__primary-text' and contains(text(), 'Türkiye')]")
))
turk.click()
time.sleep(2)
wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "input[placeholder='pasaport Numarası Giriniz']"))).send_keys("U34565375")
wait.until(EC.element_to_be_clickable((By.ID, "passportExpirtyDate"))).send_keys("24042030")
time.sleep(2)

wait.until(EC.element_to_be_clickable((By.XPATH, "//*[@class='mdc-button__label' and contains(text(), 'Kaydet')]"))).click()
time.sleep(3)

wait.until(EC.element_to_be_clickable((By.XPATH, "//*[@class='mdc-button__label' and contains(text(), 'Devam Et')]"))).click()
time.sleep(3)
wait.until(EC.element_to_be_clickable((By.XPATH, "//*[@class='mdc-button__label' and contains(text(), ' Tek Seferlik Şifre (OTP) Oluştur ')]"))).click()
time.sleep(3)
Otp = get_input_dialog("OTP Kodu", "OTP kodunu giriniz: ")
wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "input[placeholder='OTP']"))).send_keys(Otp)
time.sleep(3)
wait.until(EC.element_to_be_clickable((By.XPATH, "//*[@class='mdc-button__label' and contains(text(), ' Doğrula ')]"))).click()
time.sleep(3)
wait.until(EC.element_to_be_clickable((By.XPATH, "//*[@class='mdc-button__label' and contains(text(), 'Devam Et')]"))).click()
time.sleep(3)
wait.until(EC.element_to_be_clickable((By.CLASS_NAME,"date-availiable" ))).click()
time.sleep(3)
# Select by ID
radio_element_by_id = wait.until(EC.presence_of_element_located((By.ID, "STRadio1")))
# Example: clicking the radio button
radio_element_by_id.click()
time.sleep(3)
wait.until(EC.element_to_be_clickable((By.XPATH, "//*[@class='mdc-button__label' and contains(text(), 'Devam Et')]"))).click()
time.sleep(3)
wait.until(EC.element_to_be_clickable((By.XPATH, "//*[@class='mdc-button__label' and contains(text(), 'Devam Et')]"))).click()
time.sleep(3)