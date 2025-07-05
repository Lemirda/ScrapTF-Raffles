import os
import asyncio
import nodriver as uc
import sys

async def check_and_login():
    """
    Проверяет наличие профиля браузера и при необходимости запускает процесс авторизации.
    Возвращает True, если профиль уже существует или авторизация прошла успешно.
    """
    # Получаем путь к директории с исполняемым файлом
    if getattr(sys, 'frozen', False):
        # Если приложение запущено как исполняемый файл (exe)
        application_path = os.path.dirname(sys.executable)
    else:
        # Если приложение запущено как скрипт
        application_path = os.path.dirname(os.path.abspath(__file__))
    
    browser_profile_dir = os.path.join(application_path, "browser_profile")
    
    # Если профиль уже существует, просто возвращаем True
    if os.path.exists(browser_profile_dir):
        print("\n=== Папка профиля браузера уже существует ===")
        print(f"Путь к профилю: {browser_profile_dir}")
        return True, browser_profile_dir
    
    # Создаем директорию для профиля
    try:
        os.makedirs(browser_profile_dir)
        print(f"\n=== Создана директория для профиля браузера: {browser_profile_dir} ===")
    except Exception as e:
        print(f"Ошибка при создании директории профиля: {str(e)}")
        return False, browser_profile_dir
    
    # Запускаем процесс авторизации
    login_successful = await perform_login(browser_profile_dir)
    return login_successful, browser_profile_dir

async def perform_login(profile_dir):
    """
    Запускает браузер и дает пользователю 5 минут для авторизации.
    """
    print("\n=== ТРЕБУЕТСЯ АВТОРИЗАЦИЯ ===")
    print("Сейчас откроется браузер. Вам необходимо войти в аккаунт Steam на сайте scrap.tf")
    print("У вас есть 5 минут для авторизации.")
    
    try:
        # Запускаем браузер с указанием нашего профиля
        browser = await uc.start(
            headless=False,
            user_data_dir=profile_dir
        )
        
        # Открываем сайт для авторизации
        tab = await browser.get("https://scrap.tf/")
        
        # Даем пользователю 5 минут на авторизацию
        print("\nОжидание авторизации: 5 минут")
        for i in range(5, 0, -1):
            print(f"Осталось времени: {i} минут...")
            await asyncio.sleep(60)
        
        print("\n=== Время на авторизацию истекло ===")
        print("Надеемся, вы успели войти в аккаунт.")
        print("Браузер будет закрыт. Профиль сохранен.")
        
        # Закрываем браузер
        browser.stop()
        return True
        
    except Exception as e:
        print(f"Ошибка при авторизации: {str(e)}")
        return False

# Код для самостоятельного запуска файла
if __name__ == "__main__":
    print("=== Программа авторизации для ScrapTF ===")
    login_result, profile_path = uc.loop().run_until_complete(check_and_login())
    
    if login_result:
        print("=== Авторизация успешна ===")
        print(f"Профиль сохранен в: {profile_path}")
    else:
        print("=== Авторизация не удалась ===")
        print("Пожалуйста, попробуйте снова.") 