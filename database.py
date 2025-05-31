# database.py

import psycopg2
from psycopg2.extras import RealDictCursor
from config import settings

class Database:
    def __init__(self):
        # Открываем соединение один раз при старте приложения
        self.conn = psycopg2.connect(settings.DATABASE_DSN)
        # Вручную управляем транзакциями
        self.conn.autocommit = False

    def fetchall(self, sql, *params):
        """
        Выполняет SELECT-запрос и возвращает список словарей (RealDictCursor).
        """
        with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(sql, params)
            result = cur.fetchall()
        return result

    def fetchone(self, sql, *params):
        """
        Выполняет SELECT-запрос и возвращает одну строку (словарь) или None.
        """
        with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(sql, params)
            result = cur.fetchone()
        return result

    def execute(self, sql, *params):
        """
        Выполняет INSERT, UPDATE или DELETE. После каждого запроса коммитим.
        """
        with self.conn.cursor() as cur:
            cur.execute(sql, params)
        # После успешного выполнения — фиксируем изменения
        self.conn.commit()

    def close(self):
        """
        Вызывается при завершении приложения. Закрывает соединение.
        """
        try:
            self.conn.close()
        except Exception:
            pass

# В модуле создаём один единственный экземпляр Database
db = Database()
