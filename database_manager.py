# database_manager.py

import sqlite3
import os
from datetime import datetime

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')
# ... (Функции для работы со свечами без изменений) ...
def init_db(symbol: str): os.makedirs(DATA_DIR, exist_ok=True); db_path = os.path.join(DATA_DIR, f"{symbol.lower().replace('usdt', '')}.db"); conn = sqlite3.connect(db_path); cursor = conn.cursor(); cursor.execute('CREATE TABLE IF NOT EXISTS candles (timestamp INTEGER PRIMARY KEY, open REAL, high REAL, low REAL, close REAL)'); conn.commit(); conn.close()
def get_last_timestamp(symbol: str) -> int: db_path = os.path.join(DATA_DIR, f"{symbol.lower().replace('usdt', '')}.db"); conn = sqlite3.connect(db_path); cursor = conn.cursor(); cursor.execute('SELECT MAX(timestamp) FROM candles'); result = cursor.fetchone()[0]; conn.close(); return result if result else 0
def save_candles(symbol: str, candles: list): db_path = os.path.join(DATA_DIR, f"{symbol.lower().replace('usdt', '')}.db"); conn = sqlite3.connect(db_path); cursor = conn.cursor(); cursor.executemany('INSERT OR IGNORE INTO candles (timestamp, open, high, low, close) VALUES (:timestamp, :open, :high, :low, :close)', candles); conn.commit(); conn.close()
def load_candles(symbol: str, limit: int = 1000) -> list: db_path = os.path.join(DATA_DIR, f"{symbol.lower().replace('usdt', '')}.db"); conn = sqlite3.connect(db_path); conn.row_factory = sqlite3.Row; cursor = conn.cursor(); cursor.execute('SELECT * FROM candles ORDER BY timestamp DESC LIMIT ?', (limit,)); rows = cursor.fetchall(); conn.close(); return [dict(row) for row in reversed(rows)]

def init_signals_db():
    os.makedirs(DATA_DIR, exist_ok=True); db_path = os.path.join(DATA_DIR, 'signals.db')
    conn = sqlite3.connect(db_path); cursor = conn.cursor()
    cursor.execute('CREATE TABLE IF NOT EXISTS signals (id INTEGER PRIMARY KEY AUTOINCREMENT, timestamp TEXT, symbol TEXT, stop_loss REAL, take_profit REAL)')
    try: cursor.execute('ALTER TABLE signals ADD COLUMN take_profit_2 REAL')
    except sqlite3.OperationalError: pass
    conn.commit(); conn.close()
def save_signal(symbol: str, sl: float, tp1: float, tp2: float):
    db_path = os.path.join(DATA_DIR, 'signals.db'); conn = sqlite3.connect(db_path); cursor = conn.cursor()
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    cursor.execute('INSERT INTO signals (timestamp, symbol, stop_loss, take_profit, take_profit_2) VALUES (?, ?, ?, ?, ?)', (now, symbol, sl, tp1, tp2))
    conn.commit(); conn.close()
def load_signals() -> list:
    db_path = os.path.join(DATA_DIR, 'signals.db'); conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row; cursor = conn.cursor(); cursor.execute('SELECT * FROM signals ORDER BY id DESC')
    rows = cursor.fetchall(); conn.close(); return [dict(row) for row in rows]

# <<< НОВАЯ ФУНКЦИЯ: Удаление одного сигнала по его ID >>>
def delete_signal(signal_id: int):
    db_path = os.path.join(DATA_DIR, 'signals.db')
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute('DELETE FROM signals WHERE id = ?', (signal_id,))
    conn.commit()
    conn.close()

# <<< НОВАЯ ФУНКЦИЯ: Полная очистка таблицы сигналов >>>
def clear_all_signals():
    db_path = os.path.join(DATA_DIR, 'signals.db')
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute('DELETE FROM signals')
    conn.commit()
    conn.close()