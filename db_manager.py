import sqlite3
import datetime

class DBManager:
    def __init__(self, db_path="surveillance.db"):
        self.db_path = db_path
        self._create_table()

    def _create_table(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        # Création de la table avec la colonne camera_name comme demandé
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT,
                camera_id TEXT,
                camera_name TEXT,
                status TEXT,
                image_path TEXT
            )
        ''')
        conn.commit()
        conn.close()

    def log_event(self, camera_id, status, image_path, camera_name="Inconnu"):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute('''
            INSERT INTO logs (timestamp, camera_id, camera_name, status, image_path)
            VALUES (?, ?, ?, ?, ?)
        ''', (now_str, camera_id, camera_name, status, image_path))
        conn.commit()
        conn.close()
