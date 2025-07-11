import random
import nodriver as uc
import traceback
import asyncio
import login

from db_manager import RaffleDatabase


async def collect_raffles_from_page(tab, db):
    """Собирает раздачи с текущей страницы"""
    try:
        await tab.wait_for('#raffles-list', timeout=30)
        await asyncio.sleep(random.uniform(5.0, 10.0))

        raffle_links = await tab.evaluate('''
            Array.from(document.querySelectorAll('.panel-raffle .panel-heading a'))
                .map(a => a.href)
                .filter(href => href && href.includes('/raffles/'));
        ''')

        if not raffle_links:
            print("Не удалось найти ни одной ссылки на раздачу!")
            return 0, 0

        new_raffles = 0
        existing_raffles = 0

        for link in raffle_links:
            if isinstance(link, dict) and 'value' in link:
                link = link['value']

            if not link.startswith('https://scrap.tf'):
                link = f"https://scrap.tf{link}"

            try:
                if not db.is_raffle_exists(link):
                    if db.add_raffle(link):
                        new_raffles += 1
                else:
                    existing_raffles += 1
            except Exception as e:
                print(f"Исключение при добавлении в базу данных: {str(e)}")
                traceback.print_exc()

        return new_raffles, existing_raffles

    except Exception as e:
        print(f"Ошибка при сборе раздач: {str(e)}")
        traceback.print_exc()
        return 0, 0


async def main():
    # Проверяем авторизацию перед запуском
    print("=== Проверка авторизации ===")
    login_result, profile_path = await login.check_and_login()

    if not login_result:
        print("Ошибка авторизации. Работа программы остановлена.")
        return

    print("=== Авторизация успешна, запускаем основной скрипт ===")

    db = RaffleDatabase()

    browser = await uc.start(
        headless=False,
        user_data_dir=profile_path
    )

    try:
        print("\n=== Запускаем браузер с локальным профилем ===")
        print(f"Путь к профилю: {profile_path}")

        tab = await browser.get("https://scrap.tf/")
        await asyncio.sleep(5)

        while True:
            stats_before = db.get_stats()
            print("\n=== Новая итерация сканирования ===")
            print(
                f"Статистика перед сканированием: Всего раздач: {stats_before['total']}, Необработанных: {stats_before['unprocessed']}, Обработанных: {stats_before['processed']}")

            # Собираем раздачи с /raffles
            print("\nСканируем все раздачи...")
            tab = await browser.get("https://scrap.tf/raffles")
            await asyncio.sleep(random.uniform(5.0, 10.0))
            all_new, all_existing = await collect_raffles_from_page(tab, db)
            print(
                f"С основной страницы: {all_new} новых раздач, {all_existing} существующих")

            # Собираем раздачи с /raffles/ending
            print("\nСканируем раздачи, которые скоро закончатся...")
            tab = await browser.get("https://scrap.tf/raffles/ending")
            await asyncio.sleep(random.uniform(5.0, 10.0))
            ending_new, ending_existing = await collect_raffles_from_page(tab, db)
            print(
                f"С ending: {ending_new} новых раздач, {ending_existing} существующих")

            total_new = ending_new + all_new
            total_existing = ending_existing + all_existing
            print(
                f"\nВсего собрано: {total_new} новых раздач, {total_existing} уже существующих")

            stats_after = db.get_stats()

            print("\n--- Начинаем обработку необработанных раздач ---")
            await process_unprocessed_raffles(browser, db)

            stats_final = db.get_stats()
            print("\nИтоговая статистика:")
            print(f"Всего раздач в базе: {stats_final['total']}")
            print(f"Необработанных раздач: {stats_final['unprocessed']}")
            print(f"Обработанных раздач: {stats_final['processed']}")
            print(
                f"Обработано за этот запуск: {stats_final['processed'] - stats_after['processed']}")

            wait_minutes = random.uniform(5, 20)
            wait_seconds = int(wait_minutes * 60)
            print(f"Следующая проверка через {wait_minutes:.1f} минут")

            print(
                f"Ожидаем {wait_minutes:.1f} минут перед следующим сканированием...")
            await asyncio.sleep(wait_seconds)

    except Exception as e:
        print(f"Произошла ошибка: {str(e)}")
        print("Подробная информация об ошибке:")
        traceback.print_exc()
    finally:
        try:
            if browser:
                browser.stop()
                print("Браузер закрыт")
        except Exception as browser_error:
            print(f"Ошибка при закрытии браузера: {str(browser_error)}")
            pass

        db.close()
        print("База данных закрыта")


async def process_unprocessed_raffles(browser, db):
    unprocessed_raffles = db.get_unprocessed_raffles()

    if not unprocessed_raffles:
        print("Нет необработанных раздач для участия.")
        return

    print(
        f"Найдено {len(unprocessed_raffles)} необработанных раздач для участия.")

    processed_count = 0
    failed_count = 0

    for raffle in unprocessed_raffles:
        url = raffle['url']
        print(f"\nПереход по ссылке: {url}")

        try:
            tab = await browser.get(url)
            await asyncio.sleep(random.uniform(5.0, 10.0))

            try:
                ended_element = await tab.wait_for('.raffle-row-full-width', timeout=5)

                if ended_element:
                    print("Раздача уже закончилась. Удаляем из базы данных.")
                    db.delete_raffle(url)
                    continue
            except:
                pass  # Элемент не найден, значит раздача активна

            try:
                # Проверяем, есть ли кнопка Leave
                leave_button = await tab.wait_for('button.btn-danger.btn-lg[onclick*="LeaveRaffle"]', timeout=5)

                if leave_button:
                    print("Уже участвуем в этой раздаче.")
                    db.mark_as_processed(url)
                    processed_count += 1
                    continue
            except:
                try:
                    # Проверяем кнопку Enter
                    enter_button = await tab.wait_for('button.btn-info.btn-lg[onclick*="EnterRaffle"]:not([id="raffle-enter"])', timeout=5)

                    if enter_button:
                        is_visible = await tab.evaluate('''
                            (function() {
                                const button = document.querySelector('button.btn-info.btn-lg[onclick*="EnterRaffle"]:not([id="raffle-enter"])');
                                if (!button) return false;
                                const style = window.getComputedStyle(button);
                                return style.display !== 'none' && style.visibility !== 'hidden';
                            })();
                        ''')

                        if is_visible:
                            print("Найдена кнопка 'Enter Raffle'. Нажимаем...")
                            await enter_button.click()
                            await asyncio.sleep(random.uniform(5.0, 10.0))

                            try:
                                leave_button = await tab.wait_for('button.btn-danger.btn-lg[onclick*="LeaveRaffle"]', timeout=30)

                                if leave_button:
                                    print("Успешно вступили в раздачу!")
                                    db.mark_as_processed(url)
                                    processed_count += 1
                            except:
                                print(
                                    "Не удалось дождаться появления кнопки 'Leave Raffle'.")
                                failed_count += 1
                        else:
                            # Такого не может произойти
                            print("Раздача недоступна (кнопка Enter не видима).")
                            db.delete_raffle(url)  # Такого не может произойти
                except:
                    print("Раздача недоступна (кнопка Enter не найдена).")
                    db.delete_raffle(url)

            await asyncio.sleep(random.uniform(3.0, 5.0))

        except Exception as e:
            print(f"Ошибка при обработке раздачи {url}: {str(e)}")
            traceback.print_exc()
            failed_count += 1

    print(
        f"\nОбработка раздач завершена: успешно обработано {processed_count}, не удалось обработать {failed_count}")

if __name__ == "__main__":
    uc.loop().run_until_complete(main())
