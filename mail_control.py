import imaplib
import email
import re

def extract_otp_from_email(html_body):
    """
    Verilen HTML e-posta gövdesinden 6 haneli OTP kodunu çıkarır.
    
    Args:
        html_body (str): E-postanın ham HTML içeriği.
        
    Returns:
        str: Bulunan 6 haneli OTP kodu. Bulunamazsa None döner.
    """
    # Regex Deseni: "is " kelimesinden sonra gelen 6 rakamı bul ve yakala.
    # (\d{6}) -> \d: herhangi bir rakam, {6}: tam 6 tane olacak şekilde.
    # Parantez içi, "yakalama grubu" (capturing group) oluşturur,
    # böylece sadece bu kısmı alabiliriz.
    pattern = r"is (\d{6})"
    
    # re.search() fonksiyonu metin içinde deseni arar
    match = re.search(pattern, html_body)
    
    # Eğer bir eşleşme bulunursa...
    if match:
        # Yakalanan ilk grubu (yani 6 haneli sayıyı) döndür
        otp_code = match.group(1)
        return otp_code
    else:
        # Eşleşme bulunamazsa None döndür
        return None


def get_mail(username, password, imap_server):

    # E-POSTA HESAP BİLGİLERİ
    # DİKKAT: Şifrenizi doğrudan koda yazmak güvensizdir! Bunun yerine "Uygulama Şifreleri" kullanın.
    USERNAME = username
    PASSWORD = password # Normal şifreniz değil!
    IMAP_SERVER = imap_server

    # Sunucuya bağlan
    imap = imaplib.IMAP4_SSL(IMAP_SERVER)
    # Giriş yap
    imap.login(USERNAME, PASSWORD)

    # Gelen kutusunu seç
    status, messages = imap.select("INBOX")
    print(f"Gelen kutusunda {messages[0]} adet e-posta var.")

    # Sadece belirli bir göndericiden gelen okunmamış e-postaları ara
    # Örnek: 'noreply@ornekwebsite.com' adresinden gelenler
    status, search_result = imap.search(None, '(UNSEEN FROM "donotreply@vfshelpline.com")')
    extracted_otp = None
    # Arama sonucunda bulunan e-postaların ID'lerini işle
    for num in search_result[0].split():
        status, data = imap.fetch(num, "(RFC822)")
        for response_part in data:
            if isinstance(response_part, tuple):
                # E-postayı byte'lardan email.message objesine dönüştür
                msg = email.message_from_bytes(response_part[1])
                
                # E-postanın gövdesini al
                if msg.is_multipart():
                    # Birden fazla bölüm varsa, text/plain olanı bul
                    for part in msg.walk():
                        content_type = part.get_content_type()
                        if content_type == "text/plain":
                            try:
                                body = part.get_payload(decode=True).decode()
                                print("\n--- YENİ E-POSTA GÖVDESİ ---")
                                print(body)
                                
                                # ÖRNEK: "Doğrulama kodunuz: 123456" gibi bir metinden kodu bulma
                                match = re.search(r"Doğrulama kodunuz: (\d{6})", body)
                                if match:
                                    verification_code = match.group(1)
                                    print(f"\n>>> BULUNAN DOĞRULAMA KODU: {verification_code} <<<")
                                    return verification_code

                            except:
                                pass
                else:
                    # Tek bölüm varsa doğrudan al
                    body = msg.get_payload(decode=True).decode()
                    return body

    # Bağlantıyı kapat
    imap.close()
    imap.logout()


if __name__ == "__main__":
    print( extract_otp_from_email(get_mail(username="yunusemretom@gmail.com",imap_server="imap.gmail.com",password="hrua lyrh orka qlvt")))