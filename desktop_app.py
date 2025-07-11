"""Модуль для создания графического интерфейса приложения"""
import sys
import os
import time
import asyncio
import traceback
from datetime import datetime
from collections import deque
import psutil

from PyQt6.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTextEdit, QProgressBar, QSplitter, QFrame, QSizePolicy
from PyQt6.QtCore import Qt, pyqtSignal, QObject, QThread, QEvent
from PyQt6.QtGui import QIcon, QFont, QPalette, QPainter, QColor, QBrush, QPen
from PyQt6.QtCharts import QChart, QChartView, QValueAxis, QSplineSeries

from db_manager import RaffleDatabase
import main

# Цветовая схема
COLORS = {
    'background': QColor(18, 18, 18),
    'card_bg': QColor(30, 30, 30),
    'text': QColor(240, 240, 240),
    'text_secondary': QColor(180, 180, 180),
    'accent': QColor(75, 107, 251),
    'success': QColor(75, 225, 140),
    'warning': QColor(255, 170, 0),
    'danger': QColor(255, 88, 88),
    'chart_cpu': QColor(75, 107, 251),
    'chart_memory': QColor(75, 225, 140),
    'chart_grid': QColor(60, 60, 60),
    'network': QColor(186, 85, 211)
}


class ConsoleOutput(QObject):
    """Класс для перенаправления вывода консоли"""
    text_written = pyqtSignal(str)

    def write(self, text):
        if text.strip():
            self.text_written.emit(text.strip())

    def flush(self):
        pass


class MainWorker(QThread):
    """Рабочий поток для запуска основного скрипта"""
    status_changed = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.running = True

    def run(self):
        self.status_changed.emit("running")
        try:
            asyncio.run(main.main())
        except Exception as e:
            print(f"Ошибка в основном скрипте: {str(e)}")
            traceback.print_exc()
        finally:
            self.status_changed.emit("stopped")

    def stop(self):
        self.running = False
        self.terminate()
        self.wait()


class SystemStatsWorker(QThread):
    """Рабочий поток для сбора статистики системы"""
    stats_updated = pyqtSignal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.running = True

    def run(self):
        while self.running:
            try:
                stats = self.get_system_stats()
                self.stats_updated.emit(stats)
            except Exception as e:
                print(f"Ошибка при сборе статистики: {str(e)}")
            time.sleep(2)  # Обновление каждые 2 секунды

    def get_system_stats(self):
        cpu_percent = psutil.cpu_percent(interval=0.5)
        memory = psutil.virtual_memory()
        memory_percent = memory.percent
        net_io = psutil.net_io_counters()

        return {
            'cpu_percent': cpu_percent,
            'memory_percent': memory_percent,
            # в ГБ
            'memory_used': round(memory.used / (1024 * 1024 * 1024), 2),
            # в ГБ
            'memory_total': round(memory.total / (1024 * 1024 * 1024), 2),
            'net_sent': round(net_io.bytes_sent / (1024 * 1024), 2),  # в МБ
            'net_recv': round(net_io.bytes_recv / (1024 * 1024), 2),  # в МБ
            'timestamp': datetime.now().strftime('%H:%M:%S')
        }

    def stop(self):
        self.running = False
        self.terminate()
        self.wait()


class RaffleStatsWorker(QThread):
    """Рабочий поток для сбора статистики раздач"""
    stats_updated = pyqtSignal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.running = True

    def run(self):
        while self.running:
            try:
                db = RaffleDatabase()
                stats = db.get_stats()
                db.close()
                self.stats_updated.emit(stats)
            except Exception as e:
                print(f"Ошибка при сборе статистики раздач: {str(e)}")
            time.sleep(5)  # Обновление каждые 5 секунд

    def stop(self):
        self.running = False
        self.terminate()
        self.wait()


class ModernProgressBar(QProgressBar):
    """Современный стилизованный прогресс-бар"""

    def __init__(self, parent=None, color=COLORS['accent']):
        super().__init__(parent)
        self.setTextVisible(False)
        self.setMaximumHeight(8)
        self.color = color
        self.setStyleSheet(f"""
            QProgressBar {{
                background-color: {COLORS['card_bg'].darker(120).name()};
                border-radius: 4px;
                border: none;
            }}
            QProgressBar::chunk {{
                background-color: {color.name()};
                border-radius: 4px;
            }}
        """)


class StatsCard(QFrame):
    """Карточка для отображения статистики"""

    def __init__(self, title, icon_text, color=COLORS['accent'], parent=None):
        super().__init__(parent)
        self.color = color
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setStyleSheet(f"""
            StatsCard {{
                background-color: {COLORS['card_bg'].name()};
                border-radius: 10px;
                padding: 15px;
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)

        # Заголовок
        title_label = QLabel(title)
        title_label.setStyleSheet(
            f"color: {COLORS['text_secondary'].name()}; font-size: 14px;")

        # Значение
        self.value_label = QLabel("0")
        self.value_label.setStyleSheet(
            f"color: {COLORS['text'].name()}; font-size: 24px; font-weight: bold;")
        self.value_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Дополнительная информация
        self.details_label = QLabel("")
        self.details_label.setStyleSheet(
            f"color: {COLORS['text_secondary'].name()}; font-size: 12px;")
        self.details_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Прогресс-бар
        self.progress_bar = ModernProgressBar(color=color)

        # Иконка (используем текстовую метку для отображения иконки)
        icon_label = QLabel(icon_text)
        icon_label.setStyleSheet(f"""
            color: {color.name()};
            font-size: 20px;
            background-color: {color.darker(300).name()};
            border-radius: 20px;
            padding: 10px;
        """)
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_label.setFixedSize(40, 40)

        # Верхняя часть с иконкой и заголовком
        header_layout = QHBoxLayout()
        header_layout.addWidget(icon_label)
        header_layout.addWidget(title_label, 1)

        layout.addLayout(header_layout)
        layout.addWidget(self.value_label)
        layout.addWidget(self.details_label)
        layout.addWidget(self.progress_bar)

        self.setSizePolicy(QSizePolicy.Policy.Expanding,
                           QSizePolicy.Policy.Fixed)
        self.setMinimumHeight(150)


class ModernChart(QChartView):
    """Современный стилизованный график"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.chart = QChart()
        self.setChart(self.chart)

        # Настройка внешнего вида графика
        self.chart.setBackgroundBrush(QBrush(COLORS['card_bg']))
        self.chart.setTitleBrush(QBrush(COLORS['text']))
        self.chart.setTitleFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        self.chart.setAnimationOptions(QChart.AnimationOption.SeriesAnimations)
        self.chart.legend().setLabelBrush(QBrush(COLORS['text']))
        self.chart.legend().setAlignment(Qt.AlignmentFlag.AlignBottom)

        # Серии данных
        self.cpu_series = QSplineSeries()
        self.cpu_series.setPen(QPen(COLORS['chart_cpu'], 3))

        self.memory_series = QSplineSeries()
        self.memory_series.setPen(QPen(COLORS['chart_memory'], 3))

        # Оси
        self.axis_x = QValueAxis()
        self.axis_x.setRange(0, 30)
        self.axis_x.setLabelFormat("%d")
        self.axis_x.setLabelsColor(COLORS['text'])
        self.axis_x.setGridLineColor(COLORS['chart_grid'])
        self.axis_x.setTitleBrush(QBrush(COLORS['text']))

        self.axis_y = QValueAxis()
        self.axis_y.setRange(0, 100)
        self.axis_y.setLabelFormat("%d")
        self.axis_y.setLabelsColor(COLORS['text'])
        self.axis_y.setGridLineColor(COLORS['chart_grid'])
        self.axis_y.setTitleBrush(QBrush(COLORS['text']))

        self.chart.addSeries(self.cpu_series)
        self.chart.addSeries(self.memory_series)
        self.chart.addAxis(self.axis_x, Qt.AlignmentFlag.AlignBottom)
        self.chart.addAxis(self.axis_y, Qt.AlignmentFlag.AlignLeft)

        self.cpu_series.attachAxis(self.axis_x)
        self.cpu_series.attachAxis(self.axis_y)
        self.memory_series.attachAxis(self.axis_x)
        self.memory_series.attachAxis(self.axis_y)

        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setStyleSheet(
            f"background-color: {COLORS['card_bg'].name()}; border-radius: 10px;")


class StatsCounter(QFrame):
    """Счетчик для отображения статистики раздач"""

    def __init__(self, title, color=COLORS['accent'], parent=None):
        super().__init__(parent)
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setStyleSheet(f"""
            StatsCounter {{
                background-color: {COLORS['card_bg'].name()};
                border-radius: 10px;
                padding: 15px;
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)

        # Заголовок
        title_label = QLabel(title)
        title_label.setStyleSheet(
            f"color: {COLORS['text_secondary'].name()}; font-size: 14px; font-weight: bold;")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Значение
        self.value_label = QLabel("0")
        self.value_label.setStyleSheet(
            f"color: {color.name()}; font-size: 32px; font-weight: bold;")
        self.value_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        layout.addWidget(title_label)
        layout.addWidget(self.value_label)

        self.setSizePolicy(QSizePolicy.Policy.Expanding,
                           QSizePolicy.Policy.Fixed)


class ModernConsole(QTextEdit):
    """Современная стилизованная консоль"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setReadOnly(True)
        self.setFont(QFont("Consolas", 10))

        # Настройка полосы прокрутки
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)
        self.auto_scroll = True

        # Базовый стиль консоли
        self.setStyleSheet(f"""
            QTextEdit {{
                background-color: {COLORS['card_bg'].darker(120).name()};
                color: {COLORS['text'].name()};
                border-radius: 10px;
                padding: 10px;
                border: none;
            }}
        """)

        # Отдельно настраиваем стиль для полосы прокрутки
        scrollbar_style = f"""
            QScrollBar:vertical {{
                background-color: {COLORS['card_bg'].darker(120).name()};
                width: 14px;
                margin: 0px;
                border: none;
            }}
            QScrollBar::handle:vertical {{
                background-color: {COLORS['card_bg'].lighter(150).name()};
                border-radius: 6px;
                min-height: 20px;
                margin: 2px;
            }}
            QScrollBar::handle:vertical:hover {{
                background-color: {COLORS['accent'].name()};
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0px;
                background: none;
            }}
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
                background: none;
            }}
        """

        self.verticalScrollBar().setStyleSheet(scrollbar_style)

    def append(self, text):
        """Добавление текста с проверкой положения скроллбара"""
        # Проверяем, находится ли скроллбар внизу перед добавлением текста
        scrollbar = self.verticalScrollBar()
        at_bottom = scrollbar.value() >= scrollbar.maximum() - 10

        # Добавляем текст
        super().append(text)

        # Обновляем события, чтобы получить актуальное значение максимума скроллбара
        QApplication.processEvents()

        # Если скроллбар был внизу, прокручиваем вниз
        if at_bottom and self.auto_scroll:
            scrollbar.setValue(scrollbar.maximum())

    def showEvent(self, event):
        """Обработка события показа"""
        super().showEvent(event)
        if self.auto_scroll:
            QApplication.processEvents()
            scrollbar = self.verticalScrollBar()
            scrollbar.setValue(scrollbar.maximum())


class ScrapTFApp(QMainWindow):
    def __init__(self):
        super().__init__()

        # Настройка основного окна
        self.setWindowTitle("ScrapTF Raffles")
        self.setMinimumSize(1200, 800)

        # Загружаем иконку
        # Сначала пробуем найти иконку в той же папке, где и исполняемый файл
        icon_path = os.path.join(os.path.dirname(sys.executable if getattr(
            sys, 'frozen', False) else __file__), "icon.ico")

        # Если файл не найден, ищем в родительской директории (для случая запуска из подпапки)
        if not os.path.exists(icon_path):
            icon_path = os.path.join(os.path.dirname(os.path.dirname(
                sys.executable if getattr(sys, 'frozen', False) else __file__)), "icon.ico")

        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
        else:
            print("[Система] Иконка приложения не найдена:", icon_path)

        # Инициализация переменных
        self.cpu_data = deque(maxlen=30)
        self.memory_data = deque(maxlen=30)
        self.time_labels = deque(maxlen=30)

        # Установка темной темы для всего приложения
        self.setup_dark_theme()

        # Создание основного виджета
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)

        # Основной макет
        self.main_layout = QVBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(20, 20, 20, 20)
        self.main_layout.setSpacing(15)

        # Создание интерфейса
        self.create_ui()

        # Перенаправление вывода консоли
        self.console_output = ConsoleOutput()
        self.console_output.text_written.connect(self.update_console)
        sys.stdout = self.console_output

        # Рабочие потоки
        self.main_worker = None
        self.system_stats_worker = SystemStatsWorker()
        self.system_stats_worker.stats_updated.connect(
            self.update_system_stats)
        self.system_stats_worker.start()

        self.raffle_stats_worker = RaffleStatsWorker()
        self.raffle_stats_worker.stats_updated.connect(
            self.update_raffle_stats)
        self.raffle_stats_worker.start()

        # Запуск основного скрипта
        self.start_main_script()

        # Вывод начального сообщения
        print("[Система] Приложение запущено")

    def setup_dark_theme(self):
        """Установка темной темы для всего приложения"""
        app = QApplication.instance()
        palette = QPalette()

        palette.setColor(QPalette.ColorRole.Window, COLORS['background'])
        palette.setColor(QPalette.ColorRole.WindowText, COLORS['text'])
        palette.setColor(QPalette.ColorRole.Base, COLORS['card_bg'])
        palette.setColor(QPalette.ColorRole.AlternateBase,
                         COLORS['card_bg'].darker(120))
        palette.setColor(QPalette.ColorRole.ToolTipBase, COLORS['card_bg'])
        palette.setColor(QPalette.ColorRole.ToolTipText, COLORS['text'])
        palette.setColor(QPalette.ColorRole.Text, COLORS['text'])
        palette.setColor(QPalette.ColorRole.Button, COLORS['card_bg'])
        palette.setColor(QPalette.ColorRole.ButtonText, COLORS['text'])
        palette.setColor(QPalette.ColorRole.BrightText, Qt.GlobalColor.red)
        palette.setColor(QPalette.ColorRole.Link, COLORS['accent'])
        palette.setColor(QPalette.ColorRole.Highlight, COLORS['accent'])
        palette.setColor(QPalette.ColorRole.HighlightedText, COLORS['text'])

        app.setPalette(palette)

        # Глобальные стили
        app.setStyleSheet(f"""
            QGroupBox {{
                border: 1px solid {COLORS['card_bg'].lighter(150).name()};
                border-radius: 10px;
                margin-top: 10px;
                font-weight: bold;
                color: {COLORS['text'].name()};
            }}
            
            QGroupBox::title {{
                subcontrol-origin: margin;
                subcontrol-position: top center;
                padding: 0 5px;
            }}
            
            QLabel {{
                color: {COLORS['text'].name()};
            }}
        """)

    def create_ui(self):
        """Создание пользовательского интерфейса"""
        # Верхняя панель - системные ресурсы
        system_stats_layout = QHBoxLayout()

        # CPU карточка
        self.cpu_card = StatsCard("Процессор", "📊", COLORS['chart_cpu'])
        system_stats_layout.addWidget(self.cpu_card)

        # Память карточка
        self.memory_card = StatsCard("Память", "💾", COLORS['chart_memory'])
        system_stats_layout.addWidget(self.memory_card)

        # Сеть карточка
        self.network_card = StatsCard("Сеть", "🌐", COLORS['network'])
        system_stats_layout.addWidget(self.network_card)

        # График ресурсов
        self.chart_view = ModernChart()

        # Создаем разделитель для нижней части
        bottom_splitter = QSplitter(Qt.Orientation.Horizontal)
        bottom_splitter.setHandleWidth(1)
        bottom_splitter.setStyleSheet(
            f"QSplitter::handle {{ background-color: {COLORS['card_bg'].lighter(130).name()}; }}")

        # Левая панель - статистика раздач
        raffle_stats_widget = QWidget()
        raffle_stats_layout = QVBoxLayout(raffle_stats_widget)
        raffle_stats_layout.setContentsMargins(0, 0, 0, 0)

        # Заголовок
        raffle_stats_header = QLabel("Статистика раздач")
        raffle_stats_header.setStyleSheet(
            f"font-size: 16px; font-weight: bold; color: {COLORS['text'].name()};")
        raffle_stats_layout.addWidget(raffle_stats_header)

        # Всего раздач
        self.total_counter = StatsCounter("Всего раздач", COLORS['accent'])
        raffle_stats_layout.addWidget(self.total_counter)

        # Обработано и ожидают
        stats_layout = QHBoxLayout()

        # Обработано
        self.processed_counter = StatsCounter("Обработано", COLORS['success'])
        stats_layout.addWidget(self.processed_counter)

        # Ожидают
        self.unprocessed_counter = StatsCounter("Ожидают", COLORS['warning'])
        stats_layout.addWidget(self.unprocessed_counter)

        raffle_stats_layout.addLayout(stats_layout)
        raffle_stats_layout.addStretch()

        # Правая панель - консоль
        console_widget = QWidget()
        console_layout = QVBoxLayout(console_widget)
        console_layout.setContentsMargins(0, 0, 0, 0)

        # Заголовок
        console_header = QLabel("Лог операций")
        console_header.setStyleSheet(
            f"font-size: 16px; font-weight: bold; color: {COLORS['text'].name()};")
        console_layout.addWidget(console_header)

        # Консоль
        self.console = ModernConsole()
        console_layout.addWidget(self.console)

        # Добавляем виджеты в сплиттер
        bottom_splitter.addWidget(raffle_stats_widget)
        bottom_splitter.addWidget(console_widget)
        bottom_splitter.setStretchFactor(0, 1)
        bottom_splitter.setStretchFactor(1, 2)

        # Добавление всех виджетов в основной макет
        self.main_layout.addLayout(system_stats_layout)
        self.main_layout.addWidget(self.chart_view, 1)
        self.main_layout.addWidget(bottom_splitter, 1)

    def update_console(self, text):
        """Обновление консоли"""
        # Определяем цвет текста в зависимости от содержимого
        color = COLORS['text'].name()
        if "ошибка" in text.lower() or "error" in text.lower():
            color = COLORS['danger'].name()
        elif "успешно" in text.lower() or "success" in text.lower():
            color = COLORS['success'].name()
        elif "предупреждение" in text.lower() or "warning" in text.lower():
            color = COLORS['warning'].name()
        elif "[система]" in text.lower():
            color = COLORS['accent'].name()

        # Добавляем текст с форматированием
        self.console.append(f'<span style="color:{color};">{text}</span>')

    def update_system_stats(self, stats):
        """Обновление статистики системных ресурсов"""
        # Обновление CPU
        self.cpu_card.value_label.setText(f"{stats['cpu_percent']:.1f}%")
        self.cpu_card.progress_bar.setValue(int(stats['cpu_percent']))

        # Обновление памяти
        self.memory_card.value_label.setText(f"{stats['memory_percent']:.1f}%")
        self.memory_card.details_label.setText(
            f"{stats['memory_used']:.1f} / {stats['memory_total']:.1f} ГБ")
        self.memory_card.progress_bar.setValue(int(stats['memory_percent']))

        # Обновление сети
        self.network_card.value_label.setText(f"{stats['net_recv']:.1f} МБ")
        self.network_card.details_label.setText(
            f"Получено: {stats['net_recv']:.1f} МБ")
        self.network_card.progress_bar.setValue(
            min(int(stats['net_recv'] / 10 * 100), 100))  # 10 МБ = 100%

        # Обновление графика
        self.update_chart(stats)

    def update_chart(self, stats):
        """Обновление графика ресурсов"""
        # Добавление новых данных
        self.cpu_data.append(stats['cpu_percent'])
        self.memory_data.append(stats['memory_percent'])
        self.time_labels.append(stats['timestamp'])

        # Обновление серий данных
        self.chart_view.cpu_series.clear()
        self.chart_view.memory_series.clear()

        for i, (cpu, mem) in enumerate(zip(self.cpu_data, self.memory_data)):
            self.chart_view.cpu_series.append(i, cpu)
            self.chart_view.memory_series.append(i, mem)

    def update_raffle_stats(self, stats):
        """Обновление статистики раздач"""
        self.total_counter.value_label.setText(str(stats['total']))
        self.processed_counter.value_label.setText(str(stats['processed']))
        self.unprocessed_counter.value_label.setText(str(stats['unprocessed']))

    def start_main_script(self):
        """Запуск основного скрипта"""
        if self.main_worker is None or not self.main_worker.isRunning():
            self.main_worker = MainWorker()
            self.main_worker.status_changed.connect(self.update_script_status)
            self.main_worker.start()

    def update_script_status(self, status):
        """Обновление статуса скрипта"""
        if status == "running":
            print("[Система] Основной скрипт запущен")
        else:
            print("[Система] Основной скрипт остановлен")

    def closeEvent(self, event):
        """Обработка закрытия приложения"""
        # Остановка рабочих потоков
        if self.main_worker and self.main_worker.isRunning():
            self.main_worker.stop()

        if self.system_stats_worker.isRunning():
            self.system_stats_worker.stop()

        if self.raffle_stats_worker.isRunning():
            self.raffle_stats_worker.stop()

        # Восстановление стандартного вывода
        sys.stdout = sys.__stdout__

        super().closeEvent(event)

    def showEvent(self, event):
        """Обработка события показа окна"""
        super().showEvent(event)
        # Обновляем интерфейс при показе окна
        QApplication.processEvents()

        # Обновляем скроллбар консоли
        if hasattr(self, 'console'):
            scrollbar = self.console.verticalScrollBar()
            if self.console.auto_scroll:
                scrollbar.setValue(scrollbar.maximum())

    def changeEvent(self, event):
        """Обработка изменения состояния окна"""
        if event.type() == QEvent.Type.WindowStateChange:
            if self.windowState() & Qt.WindowState.WindowMinimized:
                pass
            elif event.oldState() & Qt.WindowState.WindowMinimized:
                # Окно восстановлено из свёрнутого состояния
                QApplication.processEvents()
                # Обновляем скроллбар консоли
                if hasattr(self, 'console') and self.console.auto_scroll:
                    scrollbar = self.console.verticalScrollBar()
                    scrollbar.setValue(scrollbar.maximum())

        super().changeEvent(event)


if __name__ == "__main__":
    app = QApplication(sys.argv)

    window = ScrapTFApp()
    window.show()
    sys.exit(app.exec())
