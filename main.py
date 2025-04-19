import random
import nodriver as uc
import traceback
from db_manager import RaffleDatabase
import asyncio

async def main():
    db = RaffleDatabase()

    browser = await uc.start(
        headless=False,
        user_data_dir="C:\\Users\\User\\AppData\\Local\\Google\\Chrome\\User Data"
    )

    try:
        while True:
            stats_before = db.get_stats()

            print("\n=== Новая итерация сканирования ===")
            print(f"Статистика перед сканированием: Всего раздач: {stats_before['total']}, Необработанных: {stats_before['unprocessed']}, Обработанных: {stats_before['processed']}")

            tab = await browser.get("https://scrap.tf/raffles/ending")

            try:
                await tab.wait_for('#raffles-list', timeout=30)
            except Exception as e:
                print(f"Не удалось дождаться загрузки контейнера с раздачами: {e}")
                continue

            try:
                await tab.wait_for('.panel-body.raffle-pagination-done', timeout=60)

                start_time = asyncio.get_event_loop().time()

                while (asyncio.get_event_loop().time() - start_time) < 20:
                    try:
                        # Используем JavaScript для скроллинга т.к вариант от nodriver херовый
                        await tab.evaluate(f'''
                            window.scrollBy({{
                                top: {random.randint(500, 800)},
                                behavior: 'smooth'
                            }});
                        ''')
                        await tab.sleep(random.uniform(1.0, 2.0))
                    except Exception as e:
                        print(f"Ошибка при скроллинге: {str(e)}")
                        await tab.sleep(1.0)

            except Exception as scroll_error:
                print(f"Ошибка при скроллинге: {str(scroll_error)}")

            try:
                raffle_links = await tab.evaluate('''
                    Array.from(document.querySelectorAll('.panel-raffle .panel-heading a'))
                        .map(a => a.href)
                        .filter(href => href && href.includes('/raffles/'));
                ''')

                if raffle_links:
                    processed_links = []

                    for link in raffle_links:
                        if isinstance(link, dict) and 'value' in link:
                            link = link['value']

                        if not link.startswith('https://scrap.tf'):
                            link = f"https://scrap.tf{link}"

                        processed_links.append(link)

                    new_raffles = 0
                    existing_raffles = 0

                    for url in processed_links:
                        try:
                            if not db.is_raffle_exists(url):
                                if db.add_raffle(url):
                                    new_raffles += 1
                            else:
                                existing_raffles += 1
                        except Exception as e:
                            print(f"Исключение при добавлении в базу данных: {str(e)}")
                            traceback.print_exc()

                    print(f"\nОбработка завершена: {new_raffles} новых раздач добавлено, {existing_raffles} уже существовало в базе данных")
                else:
                    print("Не удалось найти ни одной ссылки на раздачу!")
                    continue

            except Exception as links_error:
                print(f"Ошибка при получении ссылок: {str(links_error)}")
                traceback.print_exc()

            stats_after = db.get_stats()

            print("\n--- Начинаем обработку необработанных раздач ---")
            await process_unprocessed_raffles(browser, db)

            stats_final = db.get_stats()
            print("\nИтоговая статистика:")
            print(f"Всего раздач в базе: {stats_final['total']}")
            print(f"Необработанных раздач: {stats_final['unprocessed']}")
            print(f"Обработанных раздач: {stats_final['processed']}")
            print(f"Обработано за этот запуск: {stats_final['processed'] - stats_after['processed']}")

            wait_minutes = random.uniform(5, 20)
            wait_seconds = int(wait_minutes * 60)
            print(f"Следующая проверка через {wait_minutes:.1f} минут")

            #print("Закрываем браузер для экономии ресурсов")
            #browser.stop()

            print(f"Ожидаем {wait_minutes:.1f} минут перед следующим сканированием...")
            await asyncio.sleep(wait_seconds)

            #print("Перезапускаем браузер")

            #await asyncio.sleep(5)
            
            #browser = await uc.start(
                #=False,
                #user_data_dir="C:\\Users\\User\\AppData\\Local\\Google\\Chrome\\User Data",
                #lang="en-US"
            #)

            #await asyncio.sleep(3)

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

    print(f"Найдено {len(unprocessed_raffles)} необработанных раздач для участия.")

    processed_count = 0
    failed_count = 0

    for raffle in unprocessed_raffles:
        url = raffle['url']
        print(f"\nПереход по ссылке: {url}")

        try:
            tab = await browser.get(url)
            await tab.sleep(random.uniform(10.0, 15.0))

            try:
                ended_element = await tab.wait_for('.raffle-row-full-width', timeout=5)

                if ended_element:
                    print("Раздача уже закончилась. Удаляем из базы данных.")
                    db.delete_raffle(url)
                    continue
            except:
                pass # Элемент не найден, значит раздача активна

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
                            await tab.sleep(random.uniform(10.0, 15.0))

                            try:
                                leave_button = await tab.wait_for('button.btn-danger.btn-lg[onclick*="LeaveRaffle"]', timeout=30)

                                if leave_button:
                                    print("Успешно вступили в раздачу!")
                                    db.mark_as_processed(url)
                                    processed_count += 1
                            except:
                                print("Не удалось дождаться появления кнопки 'Leave Raffle'.")
                                failed_count += 1
                        else:
                            print("Раздача недоступна (кнопка Enter не видима).") # Такого не может произойти
                            db.delete_raffle(url) # Такого не может произойти
                except:
                    print("Раздача недоступна (кнопка Enter не найдена).")
                    db.delete_raffle(url)

            await tab.sleep(random.uniform(3.0, 5.0))

        except Exception as e:
            print(f"Ошибка при обработке раздачи {url}: {str(e)}")
            traceback.print_exc()
            failed_count += 1

    print(f"\nОбработка раздач завершена: успешно обработано {processed_count}, не удалось обработать {failed_count}")

if __name__ == "__main__":
    uc.loop().run_until_complete(main())
