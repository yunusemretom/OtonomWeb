# 🔐 Çoklu Hesap Yönetimi Rehberi

Bu rehber, VFS Global randevu kontrol scripti için çoklu hesap yönetimini açıklar.

## 📁 Dosya Yapısı

```
OtonomWeb/
├── pybas.py                    # Ana script
├── user_credentials.json       # Hesap bilgileri (SİZİN DÜZENLEYECEĞİNİZ)
└── HESAP_YONETIMI.md          # Bu rehber
```

## 🔧 Hesap Bilgilerini Düzenleme

### 1. `user_credentials.json` Dosyasını Açın

Bu dosyayı herhangi bir metin editörü ile açabilirsiniz.

### 2. Hesap Bilgilerinizi Ekleyin

```json
{
  "accounts": [
    {
      "id": 1,
      "email": "SIZIN_EMAIL@example.com",
      "password": "SIZIN_SIFRENIZ",
      "description": "Ana hesap",
      "active": true
    },
    {
      "id": 2,
      "email": "IKINCI_EMAIL@example.com", 
      "password": "IKINCI_SIFRE",
      "description": "Yedek hesap 1",
      "active": true
    },
    {
      "id": 3,
      "email": "UCUNCU_EMAIL@example.com",
      "password": "UCUNCU_SIFRE", 
      "description": "Yedek hesap 2",
      "active": true
    }
  ],
  "settings": {
    "max_retry_attempts": 3,
    "account_switch_delay": 5,
    "error_screenshot": true,
    "telegram_notifications": true
  }
}
```

### 3. Alan Açıklamaları

#### Hesap Bilgileri:
- **id**: Benzersiz hesap numarası (1, 2, 3, ...)
- **email**: VFS Global hesap e-postası
- **password**: VFS Global hesap şifresi
- **description**: Hesap açıklaması (opsiyonel)
- **active**: Hesap aktif mi? (true/false)

#### Ayarlar:
- **max_retry_attempts**: Bir hesap başarısız olursa kaç kez tekrar denensin?
- **account_switch_delay**: Hesap değiştirirken kaç saniye beklesin?
- **error_screenshot**: Hata durumunda ekran görüntüsü alsın mı?
- **telegram_notifications**: Telegram bildirimleri göndersin mi?

## 🚀 Nasıl Çalışır?

### Otomatik Hesap Değiştirme:
1. Script ilk hesap ile başlar
2. Eğer hata olursa, aynı hesap ile 3 kez dener
3. 3 deneme sonrası başarısız olursa, sıradaki hesaba geçer
4. Tüm hesaplar döngüsel olarak kullanılır

### Örnek Senaryo:
```
Döngü 1: hesap1@email.com (başarılı)
Döngü 2: hesap2@email.com (hata → hesap3@email.com)
Döngü 3: hesap3@email.com (başarılı)
Döngü 4: hesap1@email.com (başarılı)
...
```

## ⚙️ Hesap Yönetimi

### Hesap Devre Dışı Bırakma:
```json
{
  "id": 2,
  "email": "problemli@email.com",
  "password": "sifre",
  "description": "Problemli hesap",
  "active": false  // ← Bu hesap kullanılmayacak
}
```

### Yeni Hesap Ekleme:
```json
{
  "id": 4,  // Yeni ID
  "email": "yeni@email.com",
  "password": "yeni_sifre",
  "description": "Yeni hesap",
  "active": true
}
```

## 🔒 Güvenlik Notları

1. **Şifrelerinizi güvenli tutun** - Bu dosya hassas bilgiler içerir
2. **Dosyayı paylaşmayın** - `user_credentials.json` dosyasını kimseyle paylaşmayın
3. **Git'e eklemeyin** - Bu dosyayı `.gitignore`'a ekleyin

## 🐛 Sorun Giderme

### "Kullanıcı bilgileri yüklenemedi" Hatası:
- `user_credentials.json` dosyasının doğru konumda olduğundan emin olun
- JSON formatının doğru olduğunu kontrol edin

### "Aktif hesap bulunamadı" Hatası:
- En az bir hesabın `"active": true` olduğundan emin olun

### Hesap Değiştirme Çalışmıyor:
- Tüm hesapların doğru e-posta ve şifre bilgilerine sahip olduğunu kontrol edin
- VFS Global hesaplarının aktif olduğundan emin olun

## 📞 Destek

Herhangi bir sorun yaşarsanız:
1. Console çıktılarını kontrol edin
2. Hata mesajlarını not alın
3. `user_credentials.json` dosyasının formatını kontrol edin
