import sqlite3
import os
from pathlib import Path
DB = Path(os.environ.get("WELD_DB_PATH", Path(__file__).parent / "weld_inspections.db"))

def connect():
    db = sqlite3.connect(DB); db.row_factory = sqlite3.Row; return db

def init_db():
    with connect() as db:
        db.execute('''CREATE TABLE IF NOT EXISTS inspections (
          id INTEGER PRIMARY KEY AUTOINCREMENT, inspection_id TEXT UNIQUE, timestamp TEXT,
          filename TEXT, image_path TEXT, annotated_path TEXT, defect_type TEXT, confidence REAL,
          severity TEXT, verdict TEXT, processing_time REAL, report_path TEXT, summary TEXT,
          analysis_mode TEXT, bbox TEXT)''')
