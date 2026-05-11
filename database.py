import sqlite3, os, sys, json
from datetime import datetime

def _db_path() -> str:
    if getattr(sys, 'frozen', False):
        base = os.path.join(os.environ.get('APPDATA', ''), 'DeepCoreSentinel')
    else:
        base = os.path.dirname(os.path.abspath(__file__))
    os.makedirs(base, exist_ok=True)
    return os.path.join(base, 'sentinel.db')

DB_PATH = _db_path()


def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_conn()
    conn.executescript('''
        CREATE TABLE IF NOT EXISTS events (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            ts        TEXT    NOT NULL,
            category  TEXT    NOT NULL,
            etype     TEXT    NOT NULL,
            severity  INTEGER DEFAULT 0,
            title     TEXT    NOT NULL,
            details   TEXT    DEFAULT '{}'
        );

        CREATE TABLE IF NOT EXISTS alerts (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            ts          TEXT    NOT NULL,
            severity    INTEGER NOT NULL,
            title       TEXT    NOT NULL,
            description TEXT,
            category    TEXT    NOT NULL,
            status      TEXT    DEFAULT 'open',
            event_id    INTEGER
        );

        CREATE TABLE IF NOT EXISTS baselines (
            metric      TEXT    PRIMARY KEY,
            val_avg     REAL    DEFAULT 0,
            val_max     REAL    DEFAULT 0,
            samples     INTEGER DEFAULT 0,
            updated_at  TEXT    NOT NULL
        );

        CREATE TABLE IF NOT EXISTS watched_paths (
            id      INTEGER PRIMARY KEY AUTOINCREMENT,
            path    TEXT    UNIQUE NOT NULL,
            enabled INTEGER DEFAULT 1,
            added   TEXT    NOT NULL
        );

        CREATE TABLE IF NOT EXISTS file_events (
            id      INTEGER PRIMARY KEY AUTOINCREMENT,
            ts      TEXT    NOT NULL,
            etype   TEXT    NOT NULL,
            path    TEXT    NOT NULL,
            sha256  TEXT
        );

        CREATE TABLE IF NOT EXISTS agent_config (
            id       INTEGER PRIMARY KEY,
            provider TEXT    DEFAULT 'anthropic',
            api_key  TEXT    DEFAULT '',
            model    TEXT    DEFAULT 'claude-sonnet-4-6',
            autonomy TEXT    DEFAULT 'manual'
        );

        CREATE INDEX IF NOT EXISTS idx_events_ts   ON events (ts DESC);
        CREATE INDEX IF NOT EXISTS idx_alerts_ts   ON alerts (ts DESC);
        CREATE INDEX IF NOT EXISTS idx_alerts_stat ON alerts (status);
        CREATE INDEX IF NOT EXISTS idx_file_ts     ON file_events (ts DESC);
    ''')
    conn.commit()
    conn.close()


# ── EVENTS ────────────────────────────────────────────────────────────────────

def insert_event(category: str, etype: str, severity: int,
                 title: str, details: dict = None) -> int:
    conn = get_conn()
    cur = conn.execute(
        'INSERT INTO events (ts,category,etype,severity,title,details) VALUES (?,?,?,?,?,?)',
        (datetime.now().isoformat(), category, etype, severity,
         title[:500], json.dumps(details or {}))
    )
    conn.commit()
    eid = cur.lastrowid
    conn.close()
    return eid


def get_events(limit: int = 200, category: str = None) -> list:
    conn = get_conn()
    if category:
        rows = conn.execute(
            'SELECT * FROM events WHERE category=? ORDER BY ts DESC LIMIT ?',
            (category, limit)
        ).fetchall()
    else:
        rows = conn.execute(
            'SELECT * FROM events ORDER BY ts DESC LIMIT ?', (limit,)
        ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ── ALERTS ────────────────────────────────────────────────────────────────────

def insert_alert(severity: int, title: str, description: str,
                 category: str, event_id: int = None) -> int:
    conn = get_conn()
    cur = conn.execute(
        'INSERT INTO alerts (ts,severity,title,description,category,event_id) VALUES (?,?,?,?,?,?)',
        (datetime.now().isoformat(), severity, title[:500], description, category, event_id)
    )
    conn.commit()
    aid = cur.lastrowid
    conn.close()
    return aid


def get_alerts(status: str = None, limit: int = 300) -> list:
    conn = get_conn()
    if status:
        rows = conn.execute(
            'SELECT * FROM alerts WHERE status=? ORDER BY ts DESC LIMIT ?',
            (status, limit)
        ).fetchall()
    else:
        rows = conn.execute(
            'SELECT * FROM alerts ORDER BY ts DESC LIMIT ?', (limit,)
        ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def update_alert_status(alert_id: int, status: str):
    conn = get_conn()
    conn.execute('UPDATE alerts SET status=? WHERE id=?', (status, alert_id))
    conn.commit()
    conn.close()


def count_alerts_by_severity() -> dict:
    conn = get_conn()
    rows = conn.execute(
        "SELECT severity, COUNT(*) as n FROM alerts WHERE status='open' GROUP BY severity"
    ).fetchall()
    conn.close()
    result = {0: 0, 1: 0, 2: 0, 3: 0, 4: 0}
    for r in rows:
        result[r['severity']] = r['n']
    return result


# ── WATCHED PATHS ─────────────────────────────────────────────────────────────

def get_watched_paths() -> list:
    conn = get_conn()
    rows = conn.execute(
        'SELECT * FROM watched_paths WHERE enabled=1'
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def add_watched_path(path: str):
    conn = get_conn()
    conn.execute(
        'INSERT OR IGNORE INTO watched_paths (path,added) VALUES (?,?)',
        (path, datetime.now().isoformat())
    )
    conn.commit()
    conn.close()


def remove_watched_path(path_id: int):
    conn = get_conn()
    conn.execute('DELETE FROM watched_paths WHERE id=?', (path_id,))
    conn.commit()
    conn.close()


# ── FILE EVENTS ───────────────────────────────────────────────────────────────

def insert_file_event(etype: str, path: str, sha256: str = None):
    conn = get_conn()
    conn.execute(
        'INSERT INTO file_events (ts,etype,path,sha256) VALUES (?,?,?,?)',
        (datetime.now().isoformat(), etype, path, sha256)
    )
    conn.commit()
    conn.close()


def get_file_events(limit: int = 200) -> list:
    conn = get_conn()
    rows = conn.execute(
        'SELECT * FROM file_events ORDER BY ts DESC LIMIT ?', (limit,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ── AGENT CONFIG ──────────────────────────────────────────────────────────────

def get_agent_config() -> dict:
    conn = get_conn()
    row  = conn.execute('SELECT * FROM agent_config LIMIT 1').fetchone()
    conn.close()
    if row:
        return dict(row)
    return {'provider': 'anthropic', 'api_key': '', 'model': 'claude-sonnet-4-6', 'autonomy': 'manual'}


def save_agent_config(provider: str, api_key: str, model: str, autonomy: str):
    conn = get_conn()
    conn.execute('DELETE FROM agent_config')
    conn.execute(
        'INSERT INTO agent_config (provider, api_key, model, autonomy) VALUES (?,?,?,?)',
        (provider, api_key, model, autonomy)
    )
    conn.commit()
    conn.close()


# ── ESTADÍSTICAS ──────────────────────────────────────────────────────────────

def get_stats() -> dict:
    conn = get_conn()
    total_events = conn.execute('SELECT COUNT(*) FROM events').fetchone()[0]
    open_alerts  = conn.execute("SELECT COUNT(*) FROM alerts WHERE status='open'").fetchone()[0]
    critical     = conn.execute("SELECT COUNT(*) FROM alerts WHERE status='open' AND severity=4").fetchone()[0]
    high         = conn.execute("SELECT COUNT(*) FROM alerts WHERE status='open' AND severity=3").fetchone()[0]
    conn.close()
    return {
        'total_events': total_events,
        'open_alerts':  open_alerts,
        'critical':     critical,
        'high':         high,
    }
