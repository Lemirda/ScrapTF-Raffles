import sqlite3

class RaffleDatabase:
    def __init__(self, db_file="raffles.db"):
        """Инициализация базы данных."""
        self.db_file = db_file
        self.conn = None
        self.create_tables()

    def create_tables(self):
        """Создание файла базы данных."""
        conn = self.connect()
        cursor = conn.cursor()

        cursor.execute('''
        CREATE TABLE IF NOT EXISTS raffles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            url TEXT UNIQUE NOT NULL,
            processed INTEGER DEFAULT 0
        )
        ''')

        cursor.execute('CREATE INDEX IF NOT EXISTS idx_raffles_url ON raffles(url)')
        
        conn.commit()

    def connect(self):
        """Подключение к базе данных."""
        if self.conn is None:
            self.conn = sqlite3.connect(self.db_file)
            self.conn.row_factory = sqlite3.Row
        return self.conn
    
    def close(self):
        """Закрытие соединения с базой данных."""
        if self.conn:
            self.conn.close()
            self.conn = None

    def add_raffle(self, url):
        """Добавление новой раздачи в базу данных."""
        conn = self.connect()
        cursor = conn.cursor()

        try:
            cursor.execute(
                'INSERT INTO raffles (url, processed) VALUES (?, 0)',
                (url,)
            )
            conn.commit()
            rows_affected = cursor.rowcount
            return rows_affected > 0
        except sqlite3.IntegrityError as e:
            print(f"Раздача уже существует в базе данных: {e}")
            return False
        except sqlite3.Error as e:
            print(f"Ошибка SQLite при добавлении раздачи: {e}")
            return False
        except Exception as e:
            print(f"Неожиданная ошибка при добавлении раздачи: {e}")
            return False

    def delete_raffle(self, url):
        """Удаляет раздачу из базы данных."""
        conn = self.connect()
        cursor = conn.cursor()
        
        try:
            cursor.execute('DELETE FROM raffles WHERE url = ?', (url,))
            conn.commit()
            return cursor.rowcount > 0
        except sqlite3.Error as e:
            print(f"Ошибка при удалении раздачи из базы данных: {e}")
            return False

    def is_raffle_exists(self, url):
        """Проверка, существует ли раздача в базе данных."""
        conn = self.connect()
        cursor = conn.cursor()
        
        cursor.execute('SELECT 1 FROM raffles WHERE url = ?', (url,))
        return cursor.fetchone() is not None

    def mark_as_processed(self, url):
        """Отметить раздачу как обработанную."""
        conn = self.connect()
        cursor = conn.cursor()

        try:
            cursor.execute(
                'UPDATE raffles SET processed = 1 WHERE url = ?',
                (url,)
            )
            conn.commit()
            return cursor.rowcount > 0
        except sqlite3.Error as e:
            print(f"Ошибка при обновлении статуса раздачи: {e}")
            return False

    def get_unprocessed_raffles(self, limit=None):
        """Получение необработанных раздач."""
        conn = self.connect()
        cursor = conn.cursor()

        if limit is not None:
            cursor.execute(
                'SELECT * FROM raffles WHERE processed = 0 LIMIT ?',
                (limit,)
            )
        else:
            cursor.execute('SELECT * FROM raffles WHERE processed = 0')
            
        return cursor.fetchall()
    
    def get_stats(self):
        """Получение статистики по раздачам."""
        conn = self.connect()
        cursor = conn.cursor()
        
        stats = {}
        
        # Общее количество раздач
        cursor.execute('SELECT COUNT(*) FROM raffles')
        stats['total'] = cursor.fetchone()[0]
        
        # Количество необработанных раздач
        cursor.execute('SELECT COUNT(*) FROM raffles WHERE processed = 0')
        stats['unprocessed'] = cursor.fetchone()[0]
        
        # Количество обработанных раздач
        cursor.execute('SELECT COUNT(*) FROM raffles WHERE processed = 1')
        stats['processed'] = cursor.fetchone()[0]
        
        return stats