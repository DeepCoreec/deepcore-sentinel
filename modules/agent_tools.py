"""
Herramientas que Aria puede ejecutar para analizar y gestionar la seguridad.
"""
import psutil
import database as db
from monitor import MonitorService

TOOLS = [
    {
        "name": "obtener_estado_sistema",
        "description": "Obtiene el estado actual del sistema: CPU, RAM, disco, red, riesgo y alertas abiertas.",
        "input_schema": {"type": "object", "properties": {}, "required": []}
    },
    {
        "name": "listar_alertas",
        "description": "Lista las alertas de seguridad registradas. Filtra por estado.",
        "input_schema": {
            "type": "object",
            "properties": {
                "status": {
                    "type": "string",
                    "enum": ["open", "resolved", "false_positive", "all"],
                    "description": "Filtro de estado. 'all' para todas."
                },
                "limit": {"type": "integer", "description": "Máximo de alertas (default 50)"}
            },
            "required": []
        }
    },
    {
        "name": "resolver_alerta",
        "description": "Cambia el estado de una alerta (resolver, falso positivo, reabrir).",
        "input_schema": {
            "type": "object",
            "properties": {
                "alert_id": {"type": "integer", "description": "ID de la alerta"},
                "nuevo_estado": {
                    "type": "string",
                    "enum": ["resolved", "false_positive", "open"],
                    "description": "Nuevo estado"
                }
            },
            "required": ["alert_id", "nuevo_estado"]
        }
    },
    {
        "name": "listar_procesos",
        "description": "Lista procesos del sistema con nivel de riesgo, CPU y RAM.",
        "input_schema": {
            "type": "object",
            "properties": {
                "solo_sospechosos": {
                    "type": "boolean",
                    "description": "Si true, solo retorna procesos con riesgo >= 2"
                },
                "limit": {"type": "integer", "description": "Máximo de procesos (default 30)"}
            },
            "required": []
        }
    },
    {
        "name": "terminar_proceso",
        "description": "Termina un proceso por PID. Usar solo en procesos claramente maliciosos.",
        "input_schema": {
            "type": "object",
            "properties": {
                "pid":   {"type": "integer", "description": "PID del proceso"},
                "razon": {"type": "string",  "description": "Motivo justificado"}
            },
            "required": ["pid", "razon"]
        }
    },
    {
        "name": "listar_conexiones",
        "description": "Lista conexiones de red activas, incluyendo las de puertos sospechosos.",
        "input_schema": {
            "type": "object",
            "properties": {
                "solo_sospechosas": {
                    "type": "boolean",
                    "description": "Si true, solo retorna conexiones con riesgo > 0"
                }
            },
            "required": []
        }
    },
    {
        "name": "buscar_proceso",
        "description": "Busca procesos por nombre (parcial o completo).",
        "input_schema": {
            "type": "object",
            "properties": {
                "nombre": {"type": "string", "description": "Nombre o parte del nombre"}
            },
            "required": ["nombre"]
        }
    },
    {
        "name": "obtener_estadisticas",
        "description": "Estadísticas globales: eventos, alertas por severidad.",
        "input_schema": {"type": "object", "properties": {}, "required": []}
    },
    {
        "name": "agregar_ruta_vigilada",
        "description": "Agrega un archivo o directorio a la vigilancia de integridad SHA256.",
        "input_schema": {
            "type": "object",
            "properties": {
                "ruta": {"type": "string", "description": "Ruta completa a vigilar"}
            },
            "required": ["ruta"]
        }
    },
    {
        "name": "obtener_eventos_archivo",
        "description": "Obtiene eventos recientes del sistema de archivos (creados, modificados, eliminados).",
        "input_schema": {
            "type": "object",
            "properties": {
                "limit": {"type": "integer", "description": "Máximo de eventos (default 50)"}
            },
            "required": []
        }
    },
]

_SEV = {0: 'INFO', 1: 'BAJA', 2: 'MEDIA', 3: 'ALTA', 4: 'CRITICA'}


def ejecutar_herramienta(name: str, inputs: dict) -> str:
    try:
        if name == "obtener_estado_sistema":
            snap = MonitorService.get().snapshot()
            return (
                f"CPU: {snap['cpu']:.1f}% | RAM: {snap['ram']:.1f}% | "
                f"Disco: {snap['disk']:.1f}%\n"
                f"Red TX: {snap['net_sent']:.1f} KB/s | RX: {snap['net_recv']:.1f} KB/s\n"
                f"Riesgo: {snap['risk_score']}/100 | Alertas abiertas: {snap['open_alerts']}\n"
                f"Procesos activos: {len(snap['processes'])} | "
                f"Conexiones: {len(snap['connections'])}"
            )

        elif name == "listar_alertas":
            status = inputs.get('status', 'open')
            limit  = int(inputs.get('limit', 50))
            alerts = db.get_alerts(None if status == 'all' else status, limit)
            if not alerts:
                return "No hay alertas con ese filtro."
            lines = [f"{'ID':>4}  {'SEV':6}  {'FECHA':16}  {'TITULO':40}  ESTADO"]
            for a in alerts:
                lines.append(
                    f"{a['id']:>4}  {_SEV.get(a['severity'], '?'):6}  "
                    f"{a['ts'][:16]:16}  {a['title'][:40]:40}  {a['status']}"
                )
            return "\n".join(lines)

        elif name == "resolver_alerta":
            db.update_alert_status(int(inputs['alert_id']), inputs['nuevo_estado'])
            return f"Alerta #{inputs['alert_id']} actualizada a '{inputs['nuevo_estado']}'."

        elif name == "listar_procesos":
            snap  = MonitorService.get().snapshot()
            procs = snap['processes']
            if inputs.get('solo_sospechosos'):
                procs = [p for p in procs if p['risk'] >= 2]
            procs = procs[:int(inputs.get('limit', 30))]
            if not procs:
                return "No hay procesos que coincidan."
            lines = [f"{'PID':>6}  {'NOMBRE':30}  {'CPU':>6}  {'RAM':>5}  RIESGO  FLAGS"]
            for p in procs:
                flags = ','.join(p['flags']) if p['flags'] else '-'
                lines.append(
                    f"{p['pid']:>6}  {p['name'][:30]:30}  "
                    f"{p['cpu']:>5.1f}%  {p['ram']:>4.1f}%  "
                    f"{p['risk']:>6}  {flags}"
                )
            return "\n".join(lines)

        elif name == "terminar_proceso":
            pid   = int(inputs['pid'])
            razon = inputs.get('razon', 'Sin motivo especificado')
            try:
                proc  = psutil.Process(pid)
                pname = proc.name()
                proc.terminate()
                db.insert_event('agente', 'proceso_terminado', 4,
                                f'Aria terminó proceso: {pname}',
                                {'pid': pid, 'razon': razon})
                return f"Proceso PID {pid} ({pname}) terminado. Razon: {razon}"
            except psutil.NoSuchProcess:
                return f"PID {pid} no existe."
            except psutil.AccessDenied:
                return f"Acceso denegado para PID {pid}."

        elif name == "listar_conexiones":
            snap  = MonitorService.get().snapshot()
            conns = snap['connections']
            if inputs.get('solo_sospechosas'):
                conns = [c for c in conns if c['risk'] > 0]
            if not conns:
                return "No hay conexiones que coincidan."
            lines = [f"{'LOCAL':25}  {'REMOTO':25}  {'ESTADO':12}  PID  SOSPECHOSA"]
            for c in conns[:50]:
                flag = "SI" if c['risk'] > 0 else "-"
                lines.append(
                    f"{c['local']:25}  {c['remote']:25}  "
                    f"{c['status']:12}  {c['pid']:>4}  {flag}"
                )
            return "\n".join(lines)

        elif name == "buscar_proceso":
            nombre = inputs['nombre'].lower()
            snap   = MonitorService.get().snapshot()
            found  = [p for p in snap['processes'] if nombre in p['name'].lower()]
            if not found:
                return f"No se encontraron procesos con '{inputs['nombre']}'."
            lines = []
            for p in found:
                lines.append(
                    f"PID {p['pid']} | {p['name']} | CPU: {p['cpu']}% | "
                    f"RAM: {p['ram']}% | Riesgo: {p['risk']} | Exe: {p['exe']}"
                )
            return "\n".join(lines)

        elif name == "obtener_estadisticas":
            stats  = db.get_stats()
            counts = db.count_alerts_by_severity()
            return (
                f"Total eventos registrados: {stats['total_events']}\n"
                f"Alertas abiertas:  {stats['open_alerts']}\n"
                f"  CRITICA (4): {counts.get(4, 0)}\n"
                f"  ALTA    (3): {counts.get(3, 0)}\n"
                f"  MEDIA   (2): {counts.get(2, 0)}\n"
                f"  BAJA    (1): {counts.get(1, 0)}"
            )

        elif name == "agregar_ruta_vigilada":
            ruta = inputs['ruta']
            db.add_watched_path(ruta)
            return f"Ruta '{ruta}' agregada a la lista de vigilancia."

        elif name == "obtener_eventos_archivo":
            limit  = int(inputs.get('limit', 50))
            events = db.get_file_events(limit)
            if not events:
                return "No hay eventos de archivo registrados."
            lines = [f"{'FECHA':16}  {'TIPO':12}  RUTA"]
            for e in events:
                lines.append(f"{e['ts'][:16]:16}  {e['etype']:12}  {e['path']}")
            return "\n".join(lines)

        else:
            return f"Herramienta desconocida: {name}"

    except Exception as ex:
        return f"Error en {name}: {ex}"
