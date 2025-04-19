import time
import threading
import queue
import sys
import psutil
import nodriver as nd
import webbrowser
from collections import deque
from datetime import datetime
from flask import Flask, render_template, jsonify
from flask_socketio import SocketIO, emit
from db_manager import RaffleDatabase
import main

app = Flask(__name__)
app.config['SECRET_KEY'] = 'scrap-tf-secret-key'
socketio = SocketIO(app)

output_queue = queue.Queue()
script_process = None
script_thread = None
stop_script_flag = threading.Event()

main_thread = None
main_loop = None
stop_main_flag = threading.Event()

# Добавляем глобальный массив для хранения истории консоли
console_history = deque(maxlen=5000)
console_history.append("[Система] Запуск приложения")

system_stats_history = deque(maxlen=60)

SYSTEM_STATS_UPDATE_INTERVAL = 5
RAFFLE_STATS_UPDATE_INTERVAL = 10  # Интервал обновления статистики раздач (в секундах)

def get_system_stats():
    cpu_percent = psutil.cpu_percent(interval=0.5)
    memory = psutil.virtual_memory()
    memory_percent = memory.percent

    net_io = psutil.net_io_counters()

    current_time = datetime.now().strftime('%H:%M:%S')
    
    stats = {
        'cpu_percent': cpu_percent,
        'memory_percent': memory_percent,
        'memory_used': round(memory.used / (1024 * 1024 * 1024), 2),  # в ГБ
        'memory_total': round(memory.total / (1024 * 1024 * 1024), 2),  # в ГБ
        'net_sent': round(net_io.bytes_sent / (1024 * 1024), 2),  # в МБ
        'net_recv': round(net_io.bytes_recv / (1024 * 1024), 2),  # в МБ
        'timestamp': current_time,
        'datetime': datetime.now().isoformat()
    }
    
    return stats

def update_system_stats():
    while True:
        try:
            stats = get_system_stats()
            system_stats_history.append(stats)
            socketio.emit('system_stats_update', stats)
            time.sleep(SYSTEM_STATS_UPDATE_INTERVAL)
        except Exception as e:
            print(f"Ошибка при обновлении статистики: {str(e)}")
            time.sleep(SYSTEM_STATS_UPDATE_INTERVAL)

def update_raffle_stats():
    """Периодически обновляет статистику раздач и отправляет через WebSocket"""
    while True:
        try:
            db = RaffleDatabase()
            stats = db.get_stats()
            db.close()
            socketio.emit('raffle_stats_update', stats)
            time.sleep(RAFFLE_STATS_UPDATE_INTERVAL)
        except Exception as e:
            print(f"Ошибка при обновлении статистики раздач: {str(e)}")
            time.sleep(RAFFLE_STATS_UPDATE_INTERVAL)

class OutputCapture:
    def __init__(self, queue):
        self.queue = queue
        self.original_stdout = None
        
    def write(self, message):
        if message.strip():
            self.queue.put(message.strip())
            console_history.append(message.strip())
            socketio.emit('script_output', {'data': message.strip()})
        if self.original_stdout:
            self.original_stdout.write(message)
            
    def flush(self):
        if self.original_stdout:
            self.original_stdout.flush()

def run_main_script():
    """Запускает основной скрипт main.py в том же процессе"""
    output_capture = OutputCapture(output_queue)
    output_capture.original_stdout = sys.stdout
    sys.stdout = output_capture

    global main_thread

    try:
        console_history.append("[Система] Основной скрипт запущен")
        socketio.emit('script_output', {'data': '[Система] Основной скрипт запущен'})
        socketio.emit('script_status', {'status': 'running'})
        nd.loop().run_until_complete(main.main())
    except Exception as e:
        error_message = f"[ОШИБКА] Ошибка в основном скрипте: {str(e)}"
        console_history.append(error_message)
        output_queue.put(error_message)
        socketio.emit('script_output', {'data': error_message})
    finally:
        sys.stdout = output_capture.original_stdout
        console_history.append("[Система] Основной скрипт завершен")
        output_queue.put("[Система] Основной скрипт завершен")
        socketio.emit('script_output', {'data': '[Система] Основной скрипт завершен'})
        main_thread = None

def get_raffle_data():
    """Получение данных о раздачах из базы данных"""
    db = RaffleDatabase()
    stats = db.get_stats()

    conn = db.connect()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM raffles ORDER BY id DESC LIMIT 100')
    raffles = cursor.fetchall()
    db.close()
    
    return {
        "stats": stats,
        "raffles": [{
            "id": raffle["id"],
            "url": raffle["url"],
            "processed": raffle["processed"] == 1
        } for raffle in raffles]
    }

@app.route('/')
def index():
    """Главная страница"""
    return render_template('index.html')

@app.route('/api/stats')
def stats():
    """API для получения статистики"""
    db = RaffleDatabase()
    stats = db.get_stats()
    db.close()
    return jsonify(stats)

@app.route('/api/system_stats')
def system_stats():
    """API для получения текущей статистики системных ресурсов"""
    return jsonify(get_system_stats())

@app.route('/api/system_stats_history')
def system_stats_history_api():
    """API для получения истории статистики системных ресурсов"""
    return jsonify(list(system_stats_history))

@app.route('/api/raffles')
def get_raffles():
    """API для получения списка раздач"""
    data = get_raffle_data()
    return jsonify(data)

@app.route('/api/script_status')
def script_status():
    """Проверка статуса скрипта"""
    if main_thread is None or not main_thread.is_alive():
        status = "stopped"
    else:
        status = "running"
    
    return jsonify({"status": status})

@socketio.on('connect')
def handle_connect():
    """Обработка подключения клиента через WebSocket"""
    emit('script_output', {'data': '[Система] WebSocket соединение установлено'})
    
    # Отправляем текущий статус скрипта
    if main_thread is None or not main_thread.is_alive():
        status = "stopped"
    else:
        status = "running"
    
    emit('script_status', {'status': status})
    
    # Отправляем всю историю консоли новому клиенту
    for message in console_history:
        emit('script_output', {'data': message})

@socketio.on('request_output')
def handle_request_output():
    """Отправка накопленного вывода скрипта через WebSocket"""
    while not output_queue.empty():
        line = output_queue.get_nowait()
        socketio.emit('script_output', {'data': line})

# Добавляем API для получения истории консоли
@app.route('/api/console_history')
def get_console_history():
    """API для получения всей истории консоли"""
    return jsonify(list(console_history))


if __name__ == '__main__':
    main_thread = threading.Thread(target=run_main_script)
    main_thread.daemon = True
    main_thread.start()

    stats_thread = threading.Thread(target=update_system_stats)
    stats_thread.daemon = True
    stats_thread.start()
    
    # Добавляем поток обновления статистики раздач
    raffle_stats_thread = threading.Thread(target=update_raffle_stats)
    raffle_stats_thread.daemon = True
    raffle_stats_thread.start()

    def open_browser():
        time.sleep(1.5)
        webbrowser.open('http://localhost:8000')

    browser_thread = threading.Thread(target=open_browser)
    browser_thread.daemon = True
    browser_thread.start()
    
    try:
        socketio.run(app, debug=False, host='0.0.0.0', port=8000)
    finally:
        stop_main_flag.set()

        if main_thread and main_thread.is_alive():
            main_thread.join(timeout=10)