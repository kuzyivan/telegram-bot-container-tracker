import os
import shutil
import subprocess


def upload_map_to_github(html_file_path):
    repo_url = "https://github.com/kuzyivan/container-tracker-maps.git"
    repo_dir = "temp_repo"
    map_dir = os.path.join(repo_dir, "maps")
    destination_path = os.path.join(map_dir, "map.html")

    # Удаляем папку, если уже существует
    if os.path.exists(repo_dir):
        shutil.rmtree(repo_dir)

    # Настройка переменных окружения для авторизации
    env = os.environ.copy()
    env["GIT_ASKPASS"] = "/bin/echo"
    env["GIT_USERNAME"] = "kuzyivan"
    env["GIT_PASSWORD"] = "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"

    # Клонируем репозиторий
    subprocess.run(["git", "clone", repo_url, repo_dir], check=True, env=env)

    # Перемещаем файл карты в maps/
    os.makedirs(map_dir, exist_ok=True)
    shutil.copyfile(html_file_path, destination_path)

    # Коммит и пуш
    subprocess.run(["git", "-C", repo_dir, "add", "maps/map.html"], check=True, env=env)
    subprocess.run(["git", "-C", repo_dir, "commit", "-m", "update map"], check=True, env=env)
    subprocess.run(["git", "-C", repo_dir, "push"], check=True, env=env)

    # Удаляем временную папку
    shutil.rmtree(repo_dir)

    return "https://kuzyivan.github.io/container-tracker-maps/maps/map.html"
