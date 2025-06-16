import undetected_chromedriver as uc
import time

def start_browser_without_cookies():
    # Tarayıcı seçeneklerini ayarla
    options = uc.ChromeOptions()
    
    # Tarayıcıyı başlat
    driver = uc.Chrome()
    
    # Çerezleri temizle
    driver.delete_all_cookies()
    
    # Google'a git (test için)
    driver.get("https://visa.vfsglobal.com/tur/tr/fra/login")
    
    # Sayfanın yüklenmesi için kısa bir bekleme
    time.sleep(100)
    
    # Tarayıcıyı kapat
    

if __name__ == "__main__":
    start_browser_without_cookies()
