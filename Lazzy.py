import os
import subprocess
import requests
import json
import tempfile
import shutil
from collections import defaultdict

# URL do apps.json z GitHuba
GITHUB_JSON_URL = "https://raw.githubusercontent.com/mmosiek/Lazzy/main/apps.json"

def fetch_apps():
    print("Downloading list of apps from GitHub...")
    try:
        response = requests.get(GITHUB_JSON_URL, timeout=30)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error while downloading app list: {e}")
        return None

def download_file(url, filename):
    print(f"Downloading: {filename}...")
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
                        print(f"Progress: {progress:.1f}%", end='\r')
        
        print(f"Downloaded: {filename}")
        return True
    except Exception as e:
        print(f"Error while downloading {filename}: {e}")
        return False

def install_silent(installer, silent_flag):
    print(f"Installing: {installer}...")
    try:
        result = subprocess.run([installer, silent_flag], 
                              check=True, 
                              capture_output=True,
                              text=True,
                              timeout=300)
        print(f"Installed: {installer}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error while installing {installer}: {e}")
        if e.stderr:
            print(f"Details: {e.stderr}")
        return False
    except subprocess.TimeoutExpired:
        print(f"Timeout while installing {installer}")
        return False

def show_menu(apps, filter_text=None):
    print("\nAvailable apps:")
    print("0. [SELECT ALL]")

    filtered_apps = {}
    categorized_apps = defaultdict(list)

    for key, app in apps.items():
        if filter_text and filter_text.lower() not in app['name'].lower():
            continue
        filtered_apps[key] = app
        category = app.get('category', 'No category')
        categorized_apps[category].append((key, app))

    if not filtered_apps:
        print("No apps found with that search.")
        return {}

    for category, app_list in categorized_apps.items():
        print(f"\n=== {category} ===")
        for key, app in app_list:
            print(f"{key}. {app['name']}")

    return filtered_apps

def display_selected_apps(apps, selected_keys):
    print("\nSelected apps to install:")
    for key in selected_keys:
        if key in apps:
            app = apps[key]
            category = app.get('category', 'No category')
            print(f"- {app['name']} ({category})")

def main():
    apps = fetch_apps()
    if not apps:
        print("Could not get app list. Check your internet connection.")
        return

    selected_apps = []
    current_filter = ""

    while True:
        filtered_apps = show_menu(apps, current_filter)
        
        if not filtered_apps and current_filter:
            print("No matching apps. Try another word.")
            current_filter = ""
            continue
        
        choice = input("\nEnter app number to add (or 'q' to quit, 'c' to clear): ").strip().lower()

        if choice == 'q':
            break
        elif choice == 'c':
            selected_apps.clear()
            print("Selection cleared.")
            continue
        elif choice == '':
            current_filter = input("Enter search keyword: ").strip()
            continue

        if choice == "0":
            selected_apps = list(filtered_apps.keys())
            print("All apps selected.")
            break

        if choice in filtered_apps:
            if choice not in selected_apps:
                selected_apps.append(choice)
                print(f"Added: {filtered_apps[choice]['name']}")
            else:
                print("This app is already selected.")
        else:
            print("Invalid choice.")

        cont = input("Add another app? (y/n): ").strip().lower()
        if cont != 'y':
            break

    if not selected_apps:
        print("No apps selected.")
        return

    display_selected_apps(apps, selected_apps)

    confirm = input("\nStart installation? (y/n): ").strip().lower()
    if confirm != 'y':
        print("Installation cancelled.")
        return

    # Create a temporary folder for installers
    download_dir = tempfile.mkdtemp(prefix="lazzy_installers_")
    print(f"Using temporary folder: {download_dir}")

    successful_installs = 0
    total_apps = len(selected_apps)

    for i, app_key in enumerate(selected_apps, 1):
        if app_key not in apps:
            print(f"Warning: App with key {app_key} not found.")
            continue

        app = apps[app_key]
        print(f"\n[{i}/{total_apps}] Processing: {app['name']}")

        installer_path = os.path.join(download_dir, app["installer_name"])
        
        # Download installer
        if download_file(app["url"], installer_path):
            # Run installer
            if install_silent(installer_path, app["silent_flag"]):
                successful_installs += 1
            
            # Delete installer
            try:
                os.remove(installer_path)
                print(f"Deleted installer: {app['installer_name']}")
            except OSError as e:
                print(f"Error deleting installer: {e}")
        else:
            print(f"Failed to download: {app['name']}")

    print(f"\nInstallation finished. Successfully installed {successful_installs}/{total_apps} apps.")

    # Delete temporary folder
    try:
        shutil.rmtree(download_dir)
        print(f"Deleted temporary folder: {download_dir}")
    except Exception as e:
        print(f"Error deleting temp folder: {e}")

if __name__ == "__main__":
    main()
