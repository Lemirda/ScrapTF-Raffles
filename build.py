import os
import sys
import subprocess
import shutil

def install_requirements():
    """Установка необходимых зависимостей"""
    print("📦 Установка необходимых зависимостей...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])
    subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])

def build_exe():
    """Сборка .exe файла"""
    print("🔨 Начинаем сборку .exe файла...")
    
    # Очистка старых сборок
    if os.path.exists("dist"):
        shutil.rmtree("dist")
    if os.path.exists("build"):
        shutil.rmtree("build")
    
    # Параметры для PyInstaller
    pyinstaller_command = [
        "pyinstaller",
        "--onefile",
        "--name", "ScrapTF_Raffles",
        "--icon", "icon.ico",
        "--hidden-import", "engineio.async_drivers.threading",
        "--hidden-import", "eventlet.hubs.epolls",
        "--hidden-import", "eventlet.hubs.kqueue",
        "--hidden-import", "eventlet.hubs.selects",
        "--add-data", "templates;templates",
        "--add-data", "static;static",
        "app.py"
    ]
    
    try:
        subprocess.check_call(pyinstaller_command)
        print("\n✅ Сборка успешно завершена!")
        print(f"📁 Исполняемый файл находится в папке: {os.path.abspath('dist')}")
    except subprocess.CalledProcessError as e:
        print(f"❌ Ошибка при сборке: {e}")
        sys.exit(1)

def cleanup():
    """Очистка временных файлов"""
    print("🧹 Очистка временных файлов...")
    if os.path.exists("build"):
        shutil.rmtree("build")
    if os.path.exists("ScrapTF_Raffles.spec"):
        os.remove("ScrapTF_Raffles.spec")

if __name__ == "__main__":
    try:
        print("🎮 Начало процесса сборки ScrapTF Raffles Bot")
        install_requirements()
        build_exe()
        cleanup()
        print("\n🎉 Готово! Теперь вы можете запустить ScrapTF_Raffles.exe из папки dist")
    except Exception as e:
        print(f"❌ Произошла ошибка: {e}")
        sys.exit(1) 