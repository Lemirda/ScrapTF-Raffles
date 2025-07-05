import os
import sys
import subprocess
import shutil
import PyQt6

def install_requirements():
    """Установка необходимых зависимостей"""
    subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])
    subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])

def build_exe():
    """Сборка .exe файла"""
    if os.path.exists("dist"):
        shutil.rmtree("dist")

    if os.path.exists("build"):
        shutil.rmtree("build")

    desktop_app_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "desktop_app.py")

    pyinstaller_command = [
        "pyinstaller",
        "--onefile",
        "--windowed",
        "--name", "ScrapTF_Raffles",
        "--icon", "icon.ico",
        "--hidden-import", "PyQt6.QtChart",
        f"--add-data={os.path.join(os.path.dirname(PyQt6.__file__), 'Qt6', 'resources')}{os.pathsep}PyQt6/Qt6/resources",
        desktop_app_path
    ]

    subprocess.check_call(pyinstaller_command)

def cleanup():
    """Очистка временных файлов"""
    if os.path.exists("build"):
        shutil.rmtree("build")

    if os.path.exists("ScrapTF_Raffles.spec"):
        os.remove("ScrapTF_Raffles.spec")

if __name__ == "__main__":
    install_requirements()
    build_exe()
    cleanup()