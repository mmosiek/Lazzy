import os
import subprocess
import requests
import json

# URL do apps.json z GitHuba
GITHUB_JSON_URL = "https://raw.githubusercontent.com/mmosiek/Lazzy/main/apps.json"

def fetch_apps():
    print("Pobieranie listy aplikacji z GitHub...")
    try:
        response = requests.get(GITHUB_JSON_URL, timeout=30)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Blad podczas pobierania listy aplikacji: {e}")
        return None

def download_file(url, filename):
    print(f"Pobieranie: {filename}...")
    try:
        response = requests.get(url, stream=True, timeout=60)
        response.raise_for_status()
        
        total_size = int(response.headers.get('content-length', 0))
        downloaded = 0
        
        with open(filename, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
                    downloaded += len(chunk)
                    if total_size > 0:
                        progress = (downloaded / total_size) * 100
                        print(f"Postep: {progress:.1f}%", end='\r')
        
        print(f"Pobrano: {filename}")
        return True
    except Exception as e:
        print(f"Blad podczas pobierania {filename}: {e}")
        return False

def install_silent(installer, silent_flag):
    print(f"Instalowanie: {installer}...")
    try:
        result = subprocess.run([installer, silent_flag], 
                              check=True, 
                              capture_output=True,
                              text=True,
                              timeout=300)
        print(f"Zainstalowano: {installer}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"Blad podczas instalacji {installer}: {e}")
        if e.stderr:
            print(f"Szczegoly bledu: {e.stderr}")
        return False
    except subprocess.TimeoutExpired:
        print(f"Timeout podczas instalacji {installer}")
        return False

def show_menu(apps, filter_text=None):
    print("\nDostepne aplikacje:")
    print("0. [WYBIERZ WSZYSTKIE]")
    
    filtered_apps = {}
    for key, app in apps.items():
        if filter_text and filter_text.lower() not in app['name'].lower():
            continue
        filtered_apps[key] = app
    
    if not filtered_apps:
        print("Brak aplikacji spelniajacych kryteria wyszukiwania.")
        return filtered_apps
    
    for key, app in filtered_apps.items():
        category = app.get('category', 'Brak kategorii')
        print(f"{key}. {app['name']} ({category})")
    
    return filtered_apps

def display_selected_apps(apps, selected_keys):
    print("\nWybrane aplikacje do instalacji:")
    for key in selected_keys:
        if key in apps:
            app = apps[key]
            category = app.get('category', 'Brak kategorii')
            print(f"- {app['name']} ({category})")

def main():
    apps = fetch_apps()
    if not apps:
        print("Nie mozna pobrac listy aplikacji. Sprawdz polaczenie internetowe.")
        return

    selected_apps = []
    current_filter = ""

    while True:
        filtered_apps = show_menu(apps, current_filter)
        
        if not filtered_apps and current_filter:
            print("Brak aplikacji spelniajacych kryteria. Sprobuj innej frazy.")
            current_filter = ""
            continue
        
        choice = input("\nWybierz numer aplikacji do dodania (lub 'q' aby zakonczyc, 'c' aby wyczyscic): ").strip().lower()

        if choice == 'q':
            break
        elif choice == 'c':
            selected_apps.clear()
            print("Wyczyszczono liste wybranych aplikacji.")
            continue
        elif choice == '':
            current_filter = input("Wpisz fragment nazwy aplikacji do wyszukania: ").strip()
            continue

        if choice == "0":
            selected_apps = list(filtered_apps.keys())
            print("Wybrano wszystkie dostepne aplikacje.")
            break

        if choice in filtered_apps:
            if choice not in selected_apps:
                selected_apps.append(choice)
                print(f"Dodano: {filtered_apps[choice]['name']}")
            else:
                print("Ta aplikacja juz zostala dodana.")
        else:
            print("Nieprawidlowy wybor.")

        cont = input("Czy chcesz dodac kolejna aplikacje? (t/n): ").strip().lower()
        if cont != 't':
            break

    if not selected_apps:
        print("Nie wybrano zadnych aplikacji.")
        return

    display_selected_apps(apps, selected_apps)

    confirm = input("\nCzy chcesz rozpoczac instalacje? (t/n): ").strip().lower()
    if confirm != 't':
        print("Instalacja anulowana.")
        return

    # Utworz folder dla pobranych instalatorow
    download_dir = "downloads"
    os.makedirs(download_dir, exist_ok=True)

    successful_installs = 0
    total_apps = len(selected_apps)

    for i, app_key in enumerate(selected_apps, 1):
        if app_key not in apps:
            print(f"Ostrzezenie: Aplikacja o kluczu {app_key} nie istnieje w liscie.")
            continue

        app = apps[app_key]
        print(f"\n[{i}/{total_apps}] Przetwarzanie: {app['name']}")

        installer_path = os.path.join(download_dir, app["installer_name"])
        
        # Pobierz plik
        if download_file(app["url"], installer_path):
            # Zainstaluj
            if install_silent(installer_path, app["silent_flag"]):
                successful_installs += 1
            
            # Usun instalator
            try:
                os.remove(installer_path)
                print(f"Usunieto instalator {app['installer_name']}")
            except OSError as e:
                print(f"Blad podczas usuwania instalatora: {e}")
        else:
            print(f"Nie udalo sie pobrac aplikacji: {app['name']}")

    print(f"\nInstalacja zakonczona. Pomyslnie zainstalowano {successful_installs}/{total_apps} aplikacji.")

    # Sprzatanie - usun puste foldery
    try:
        if not os.listdir(download_dir):
            os.rmdir(download_dir)
    except OSError:
        pass

if __name__ == "__main__":
    main()
