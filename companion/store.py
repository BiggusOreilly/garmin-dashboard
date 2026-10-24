"""Private SQLite cache. Never serve database files or arbitrary local paths."""
import json
import os
import sqlite3
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parent.parent

def now():
    return datetime.now(timezone.utc).isoformat()

class Store:
    def __init__(self, directory=None):
        self.directory = Path(directory or ROOT / 'data')
        self.directory.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.directory.chmod(0o700)
        self.db = sqlite3.connect(self.directory / 'dashboard.sqlite3', timeout=30)
        (self.directory / 'dashboard.sqlite3').chmod(0o600)
        self.db.executescript('''
        CREATE TABLE IF NOT EXISTS records(dataset TEXT, id TEXT, payload TEXT NOT NULL, fetched TEXT NOT NULL, PRIMARY KEY(dataset,id));
        CREATE TABLE IF NOT EXISTS metadata(key TEXT PRIMARY KEY, value TEXT NOT NULL);
        ''')
    def put(self, dataset, key, payload):
        self.db.execute('INSERT OR REPLACE INTO records VALUES(?,?,?,?)',(dataset,str(key),json.dumps(payload,allow_nan=False),now()))
        self.db.commit()
    def get(self, dataset, key):
        row=self.db.execute('SELECT payload FROM records WHERE dataset=? AND id=?',(dataset,str(key))).fetchone()
        return json.loads(row[0]) if row else None
    def all(self, dataset):
        return [json.loads(r[0]) for r in self.db.execute('SELECT payload FROM records WHERE dataset=? ORDER BY fetched,id',(dataset,))]
    def items(self, dataset):
        return [(r[0],json.loads(r[1])) for r in self.db.execute('SELECT id,payload FROM records WHERE dataset=? ORDER BY fetched,id',(dataset,))]
    def meta(self, key, value=None):
        if value is not None:
            self.db.execute('INSERT OR REPLACE INTO metadata VALUES(?,?)',(key,json.dumps(value)));self.db.commit()
        row=self.db.execute('SELECT value FROM metadata WHERE key=?',(key,)).fetchone()
        return json.loads(row[0]) if row else None
    def close(self):
        self.db.close()
