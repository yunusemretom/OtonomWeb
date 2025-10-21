import requests

def check_version(current_version):
    url = "https://raw.githubusercontent.com/yunusemretom/OtonomWeb/main/version.txt"
    remote_version = requests.get(url).text.strip()
    print(f"Yerel sürüm: {current_version}, Uzak sürüm: {remote_version}")

    if current_version <= remote_version:
        print("Yeni güncelleme var!")
        with open("version.txt", "w", encoding="utf-8") as f:
            f.write(remote_version)
        return True
    
    else:
        print("Güncel sürüm.")
        return False

def get_local_version(file_path="version.txt"):
    try:
        with open(file_path, "r", encoding="utf-8") as file:
            version = file.read().strip()
            return version
    except FileNotFoundError:
        print("Yerel sürüm dosyası bulunamadı!")
        return None
    except Exception as e:
        print(f"Hata oluştu: {e}")
        return None

def download_latest():
    download_url = "https://raw.githubusercontent.com/yunusemretom/OtonomWeb/main/pybas.py"
    
    r = requests.get(download_url)
    with open("main.py", "w", encoding="utf-8") as f:
        f.write(r.text)
    print("Yeni sürüm indirildi.")



if __name__ == "__main__":
    version = get_local_version()
    if version and check_version(version):
        print("Güncelleme mevcut, indiriliyor...")
        download_latest()
    else:
        print("Güncelleme gerekli değil.")