"""
Monitor Service — hilo de fondo que recolecta métricas y genera alertas.
"""
import threading, time, psutil, hashlib, os
from collections import deque
from datetime import datetime
import database as db

# Nombres de procesos conocidos como herramientas de hacking/malware
_SUSPICIOUS_NAMES = {
    'mimikatz', 'procdump', 'meterpreter', 'cobaltstrike', 'cobalt',
    'nc.exe', 'ncat', 'ncat.exe', 'netcat', 'xmrig', 'minergate',
    'nheqminer', 'wannacry', 'petya', 'lazagne', 'pwdump',
    'wce.exe', 'gsecdump', 'fgdump', 'lsadump', 'pwcrack',
}

# Rutas inusuales para ejecutables (Windows)
_SUSPICIOUS_PATHS = {
    '\\temp\\', '\\tmp\\', 'appdata\\local\\temp\\',
    'users\\public\\', 'windows\\temp\\', 'recycle',
}

# Puertos asociados a C2 / herramientas ofensivas
_SUSPICIOUS_PORTS = {
    4444, 4445, 4446,   # Metasploit
    5555, 5556,         # ADB / Meterpreter
    1337, 31337,        # Tradición hacker
    6666, 6667, 6668, 6669,  # IRC / C2
    9001, 9030,         # Tor
    8888, 7777,         # Backdoors comunes
}

_ALERT_COOLDOWN = {}     # título → última vez alertado (anti-spam)
_ALERT_COOLDOWN_SEC = 120


class MonitorService:
    _instance = None
    _lock = threading.Lock()

    @classmethod
    def get(cls) -> 'MonitorService':
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def __init__(self):
        self.running = False

        # Historial de métricas (60 puntos = ~2 min a 2s/punto)
        self.cpu_hist    = deque([0.0] * 60, maxlen=60)
        self.ram_hist    = deque([0.0] * 60, maxlen=60)
        self.net_s_hist  = deque([0.0] * 60, maxlen=60)
        self.net_r_hist  = deque([0.0] * 60, maxlen=60)

        # Estado actual
        self.cpu       = 0.0
        self.ram       = 0.0
        self.disk      = 0.0
        self.net_sent  = 0.0    # KB/s
        self.net_recv  = 0.0    # KB/s
        self.processes = []
        self.connections = []
        self.risk_score  = 0
        self.open_alerts = 0

        self._net_prev   = psutil.net_io_counters()
        self._net_time   = time.time()
        self._known_pids = set()
        self._data_lock  = threading.Lock()

    # ── Control ───────────────────────────────────────────────────────────────

    def start(self):
        if self.running:
            return
        self.running = True
        t = threading.Thread(target=self._loop, daemon=True, name='SentinelMonitor')
        t.start()

    def stop(self):
        self.running = False

    # ── Loop principal ────────────────────────────────────────────────────────

    def _loop(self):
        cycle = 0
        while self.running:
            try:
                self._collect_system()
                if cycle % 2 == 0:     # cada ~4s
                    self._collect_processes()
                    self._collect_connections()
                    self._calc_risk()
                    self._update_alert_count()
            except Exception:
                pass
            cycle += 1
            time.sleep(2)

    # ── Recolección de datos ──────────────────────────────────────────────────

    def _collect_system(self):
        cpu  = psutil.cpu_percent()
        ram  = psutil.virtual_memory().percent
        disk = psutil.disk_usage('/').percent if os.name != 'nt' else \
               psutil.disk_usage('C:\\').percent

        now   = time.time()
        net   = psutil.net_io_counters()
        dt    = max(now - self._net_time, 0.1)
        s_kb  = (net.bytes_sent - self._net_prev.bytes_sent) / 1024 / dt
        r_kb  = (net.bytes_recv - self._net_prev.bytes_recv) / 1024 / dt
        self._net_prev = net
        self._net_time = now

        with self._data_lock:
            self.cpu  = cpu
            self.ram  = ram
            self.disk = disk
            self.net_sent = max(s_kb, 0)
            self.net_recv = max(r_kb, 0)
            self.cpu_hist.append(cpu)
            self.ram_hist.append(ram)
            self.net_s_hist.append(max(s_kb, 0))
            self.net_r_hist.append(max(r_kb, 0))

        # Alerta CPU sostenida
        if cpu > 90:
            self._maybe_alert(3, f'CPU al {cpu:.0f}%',
                              'Uso crítico de procesador sostenido.', 'sistema')
        elif cpu > 75:
            self._maybe_alert(2, f'CPU al {cpu:.0f}%',
                              'Uso elevado de procesador.', 'sistema')

    def _collect_processes(self):
        procs = []
        current_pids = set()
        for p in psutil.process_iter(['pid','name','exe','cpu_percent',
                                       'memory_percent','username','status']):
            try:
                info = p.info
                pid  = info['pid']
                current_pids.add(pid)
                name = (info['name'] or '').lower()
                exe  = (info['exe']  or '').lower()

                risk = 0
                flags = []

                # Nombre sospechoso
                if any(s in name for s in _SUSPICIOUS_NAMES):
                    risk = 4
                    flags.append('nombre-sospechoso')

                # Ruta sospechosa
                if any(p in exe for p in _SUSPICIOUS_PATHS):
                    risk = max(risk, 3)
                    flags.append('ruta-inusual')

                # CPU alta individual
                if (info['cpu_percent'] or 0) > 85:
                    risk = max(risk, 2)
                    flags.append('cpu-alta')

                procs.append({
                    'pid':    pid,
                    'name':   info['name'] or '?',
                    'exe':    info['exe']  or '',
                    'cpu':    round(info['cpu_percent'] or 0, 1),
                    'ram':    round(info['memory_percent'] or 0, 1),
                    'user':   info['username'] or '',
                    'status': info['status']  or '',
                    'risk':   risk,
                    'flags':  flags,
                })

                # Proceso nuevo y sospechoso
                if pid not in self._known_pids and risk >= 3:
                    self._maybe_alert(
                        risk,
                        f'Proceso sospechoso: {info["name"]}',
                        f'PID {pid} | Ruta: {exe} | Flags: {", ".join(flags)}',
                        'proceso'
                    )
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass

        self._known_pids = current_pids
        with self._data_lock:
            self.processes = sorted(procs, key=lambda x: x['risk'], reverse=True)

    def _collect_connections(self):
        conns = []
        try:
            for c in psutil.net_connections(kind='inet'):
                if not c.raddr:
                    continue
                remote_port = c.raddr.port
                risk = 0
                if remote_port in _SUSPICIOUS_PORTS:
                    risk = 3
                    self._maybe_alert(
                        3,
                        f'Conexion a puerto sospechoso: {remote_port}',
                        f'IP: {c.raddr.ip}:{remote_port} | Estado: {c.status}',
                        'red'
                    )
                conns.append({
                    'local':  f'{c.laddr.ip}:{c.laddr.port}',
                    'remote': f'{c.raddr.ip}:{c.raddr.port}',
                    'remote_ip':   c.raddr.ip,
                    'remote_port': remote_port,
                    'status': c.status,
                    'pid':    c.pid or 0,
                    'risk':   risk,
                })
        except Exception:
            pass
        with self._data_lock:
            self.connections = conns

    def _calc_risk(self):
        score = 0
        counts = db.count_alerts_by_severity()
        score += min(counts.get(4, 0) * 25, 40)
        score += min(counts.get(3, 0) * 10, 25)
        score += min(counts.get(2, 0) * 3,  15)
        # Bonus por métricas
        if self.cpu > 85:
            score += 10
        with self._data_lock:
            self.risk_score = min(score, 100)

    def _update_alert_count(self):
        stats = db.get_stats()
        with self._data_lock:
            self.open_alerts = stats['open_alerts']

    # ── Generación de alertas con cooldown ────────────────────────────────────

    def _maybe_alert(self, severity: int, title: str, desc: str, category: str):
        now = time.time()
        if now - _ALERT_COOLDOWN.get(title, 0) < _ALERT_COOLDOWN_SEC:
            return
        _ALERT_COOLDOWN[title] = now
        db.insert_alert(severity, title, desc, category)

    # ── Getters thread-safe ───────────────────────────────────────────────────

    def snapshot(self) -> dict:
        with self._data_lock:
            return {
                'cpu':         self.cpu,
                'ram':         self.ram,
                'disk':        self.disk,
                'net_sent':    self.net_sent,
                'net_recv':    self.net_recv,
                'cpu_hist':    list(self.cpu_hist),
                'ram_hist':    list(self.ram_hist),
                'net_s_hist':  list(self.net_s_hist),
                'net_r_hist':  list(self.net_r_hist),
                'processes':   list(self.processes),
                'connections': list(self.connections),
                'risk_score':  self.risk_score,
                'open_alerts': self.open_alerts,
            }
