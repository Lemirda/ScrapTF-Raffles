import os
import shutil
import PyQt6

from PyInstaller.__main__ import run as pyinstaller_run


def cleanup():
    """Очистка временных файлов"""
    if os.path.exists("build"):
        shutil.rmtree("build")

    if os.path.exists("ScrapTF_Raffles.spec"):
        os.remove("ScrapTF_Raffles.spec")


def build_exe():
    """Сборка .exe файла"""
    if os.path.exists("dist"):
        shutil.rmtree("dist")

    if os.path.exists("build"):
        shutil.rmtree("build")

    desktop_app_path = os.path.join(os.path.dirname(
        os.path.abspath(__file__)), "desktop_app.py")

    pyinstaller_args = [
        "--onefile",
        "--windowed",
        "--name", "ScrapTF_Raffles",
        "--icon", "icon.ico",
        "--hidden-import", "PyQt6.QtChart",
        f"--add-data={os.path.join(os.path.dirname(PyQt6.__file__), 'Qt6', 'resources')}{os.pathsep}PyQt6/Qt6/resources",
        desktop_app_path
    ]

    pyinstaller_run(pyinstaller_args)


if __name__ == "__main__":
    build_exe()
    cleanup()
