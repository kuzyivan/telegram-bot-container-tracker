import os
import subprocess
import shutil
from datetime import datetime

GITHUB_USERNAME = "kuzyivan"
REPO_NAME = "container-tracker-maps"
MAP_FOLDER = "maps"
TOKEN = "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"
REPO_URL = f"https://{TOKEN}@github.com/{GITHUB_USERNAME}/{REPO_NAME}.git"

def upload_map_to_github(html_file_path):
    filename = os.path.basename(html_file_path)

    if not os.path.exists(REPO_NAME):
        subprocess.run(["git", "clone", REPO_URL])

    map_dir = os.path.join(REPO_NAME, MAP_FOLDER)
    os.makedirs(map_dir, exist_ok=True)

    destination_path = os.path.join(map_dir, filename)
    shutil.copyfile(html_file_path, destination_path)

    os.chdir(REPO_NAME)
    subprocess.run(["git", "add", os.path.join(MAP_FOLDER, filename)])
    subprocess.run(["git", "commit", "-m", f"Add map for {filename} [{datetime.now()}]"])
    subprocess.run(["git", "push"])
    os.chdir("..")

    public_url = f"https://{GITHUB_USERNAME}.github.io/{REPO_NAME}/{MAP_FOLDER}/{filename}"
    return public_url
