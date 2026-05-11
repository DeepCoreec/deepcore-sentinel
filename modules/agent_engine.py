"""
Motor de IA multi-proveedor con modo autónomo.
Soporta Anthropic (Claude), OpenAI (GPT) y Google (Gemini).
"""
import json
import threading
import time

try:
    import requests as _rq
    _HAS_REQUESTS = True
except ImportError:
    _HAS_REQUESTS = False

import database as db
from monitor import MonitorService
from modules.agent_tools import TOOLS, ejecutar_herramienta

SYSTEM_PROMPT = """Eres Aria, el agente de inteligencia artificial de DeepCore Sentinel — plataforma de seguridad empresarial para Windows.

Tu rol: analizar el estado de seguridad del sistema, investigar amenazas y ayudar al administrador a tomar decisiones de protección. Tienes acceso a herramientas en tiempo real.

Principios operativos:
1. Analiza PRIMERO con herramientas, actúa después. Nunca actúes a ciegas.
2. Sé directo y técnico. El administrador es profesional de TI.
3. Cuando termines un proceso, justifica la decisión con evidencia.
4. En duda, sugiere en lugar de actuar automáticamente.
5. Responde siempre en español.
6. Prioriza alertas CRITICA y ALTA sobre el resto."""


class AgentEngine:
    PROVIDERS = {
        'anthropic': {
            'models': ['claude-opus-4-7', 'claude-sonnet-4-6', 'claude-haiku-4-5-20251001'],
            'default': 'claude-sonnet-4-6',
        },
        'openai': {
            'models': ['gpt-4o', 'gpt-4-turbo', 'gpt-4o-mini'],
            'default': 'gpt-4o',
        },
        'gemini': {
            'models': ['gemini-2.0-flash', 'gemini-1.5-pro', 'gemini-1.5-flash'],
            'default': 'gemini-2.0-flash',
        },
    }

    def __init__(self):
        self._auto_running = False
        self._on_auto_msg  = None
        self._config       = db.get_agent_config()

    def reload_config(self):
        self._config = db.get_agent_config()

    @property
    def provider(self) -> str:
        return self._config.get('provider', 'anthropic')

    @property
    def api_key(self) -> str:
        return self._config.get('api_key', '')

    @property
    def model(self) -> str:
        cfg_model = self._config.get('model', '')
        if cfg_model:
            return cfg_model
        return self.PROVIDERS.get(self.provider, {}).get('default', '')

    @property
    def autonomy(self) -> str:
        return self._config.get('autonomy', 'manual')

    def is_configured(self) -> bool:
        return bool(self.api_key.strip())

    # ── Chat público ──────────────────────────────────────────────────────────

    def chat(self, messages: list, on_tool: callable,
             on_done: callable, on_error: callable):
        if not _HAS_REQUESTS:
            on_error("El módulo 'requests' no está instalado.")
            return
        if not self.is_configured():
            on_error("Configura tu API Key en el panel de configuración.")
            return
        threading.Thread(
            target=self._run_chat,
            args=(messages, on_tool, on_done, on_error),
            daemon=True
        ).start()

    def _run_chat(self, messages, on_tool, on_done, on_error):
        try:
            result = self._dispatch(messages, on_tool)
            on_done(result)
        except Exception as ex:
            on_error(str(ex))

    def _dispatch(self, messages: list, on_tool: callable) -> str:
        p = self.provider
        if p == 'anthropic':
            return self._chat_anthropic(messages, on_tool)
        elif p == 'openai':
            return self._chat_openai(messages, on_tool)
        elif p == 'gemini':
            return self._chat_gemini(messages, on_tool)
        raise ValueError(f"Proveedor no soportado: {p}")

    # ── Anthropic ─────────────────────────────────────────────────────────────

    def _chat_anthropic(self, messages: list, on_tool: callable) -> str:
        headers = {
            'x-api-key':         self.api_key,
            'anthropic-version': '2023-06-01',
            'content-type':      'application/json',
        }
        msgs = list(messages)

        for _ in range(12):
            body = {
                'model':      self.model,
                'max_tokens': 4096,
                'system':     SYSTEM_PROMPT,
                'messages':   msgs,
                'tools':      TOOLS,
            }
            resp = _rq.post('https://api.anthropic.com/v1/messages',
                            headers=headers, json=body, timeout=60)
            if resp.status_code != 200:
                raise Exception(f"Anthropic {resp.status_code}: {resp.text[:300]}")

            data    = resp.json()
            stop    = data.get('stop_reason')
            content = data.get('content', [])

            if stop == 'end_turn':
                return '\n'.join(b['text'] for b in content if b.get('type') == 'text')

            if stop == 'tool_use':
                msgs.append({'role': 'assistant', 'content': content})
                results = []
                for block in content:
                    if block.get('type') == 'tool_use':
                        tname, tinput = block['name'], block.get('input', {})
                        if on_tool:
                            on_tool(tname, tinput)
                        results.append({
                            'type':        'tool_result',
                            'tool_use_id': block['id'],
                            'content':     ejecutar_herramienta(tname, tinput),
                        })
                msgs.append({'role': 'user', 'content': results})
            else:
                return '\n'.join(b['text'] for b in content if b.get('type') == 'text') or '[Sin respuesta]'

        return "[Max iteraciones alcanzado]"

    # ── OpenAI ────────────────────────────────────────────────────────────────

    def _chat_openai(self, messages: list, on_tool: callable) -> str:
        headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type':  'application/json',
        }
        # Convertir tools al formato OpenAI
        oai_tools = [
            {
                'type': 'function',
                'function': {
                    'name':        t['name'],
                    'description': t['description'],
                    'parameters':  t['input_schema'],
                }
            }
            for t in TOOLS
        ]
        msgs = [{'role': 'system', 'content': SYSTEM_PROMPT}] + list(messages)

        for _ in range(12):
            body = {
                'model':    self.model,
                'messages': msgs,
                'tools':    oai_tools,
            }
            resp = _rq.post('https://api.openai.com/v1/chat/completions',
                            headers=headers, json=body, timeout=60)
            if resp.status_code != 200:
                raise Exception(f"OpenAI {resp.status_code}: {resp.text[:300]}")

            data   = resp.json()
            choice = data['choices'][0]
            msg    = choice['message']
            finish = choice['finish_reason']

            if finish == 'stop':
                return msg.get('content') or '[Sin respuesta]'

            if finish == 'tool_calls':
                msgs.append(msg)
                for tc in msg.get('tool_calls', []):
                    tname  = tc['function']['name']
                    tinput = json.loads(tc['function'].get('arguments', '{}'))
                    if on_tool:
                        on_tool(tname, tinput)
                    msgs.append({
                        'role':         'tool',
                        'tool_call_id': tc['id'],
                        'content':      ejecutar_herramienta(tname, tinput),
                    })
            else:
                return msg.get('content') or '[Sin respuesta]'

        return "[Max iteraciones alcanzado]"

    # ── Google Gemini ─────────────────────────────────────────────────────────

    def _chat_gemini(self, messages: list, on_tool: callable) -> str:
        gemini_tools = [{
            'functionDeclarations': [
                {
                    'name':        t['name'],
                    'description': t['description'],
                    'parameters':  t['input_schema'],
                }
                for t in TOOLS
            ]
        }]
        model = self.model
        url   = (f'https://generativelanguage.googleapis.com/v1beta/models/'
                 f'{model}:generateContent?key={self.api_key}')

        def _to_gemini(msgs):
            out = []
            for m in msgs:
                role    = 'model' if m['role'] == 'assistant' else 'user'
                content = m['content']
                if isinstance(content, str):
                    out.append({'role': role, 'parts': [{'text': content}]})
                elif isinstance(content, list):
                    parts = []
                    for item in content:
                        if 'text' in item:
                            parts.append({'text': item['text']})
                        elif 'functionCall' in item:
                            parts.append({'functionCall': item['functionCall']})
                        elif 'functionResponse' in item:
                            parts.append({'functionResponse': item['functionResponse']})
                    if parts:
                        out.append({'role': role, 'parts': parts})
            return out

        gemini_msgs = _to_gemini(list(messages))

        for _ in range(12):
            body = {
                'contents':          gemini_msgs,
                'tools':             gemini_tools,
                'systemInstruction': {'parts': [{'text': SYSTEM_PROMPT}]},
                'generationConfig':  {'maxOutputTokens': 4096},
            }
            resp = _rq.post(url, json=body, timeout=60)
            if resp.status_code != 200:
                raise Exception(f"Gemini {resp.status_code}: {resp.text[:300]}")

            data      = resp.json()
            candidate = data['candidates'][0]
            parts     = candidate['content']['parts']
            fn_calls  = [p for p in parts if 'functionCall' in p]
            texts     = [p['text'] for p in parts if 'text' in p]

            if not fn_calls:
                return '\n'.join(texts) or '[Sin respuesta]'

            gemini_msgs.append({'role': 'model', 'parts': parts})
            fn_responses = []
            for part in fn_calls:
                fc     = part['functionCall']
                tname  = fc['name']
                tinput = fc.get('args', {})
                if on_tool:
                    on_tool(tname, tinput)
                fn_responses.append({
                    'functionResponse': {
                        'name':     tname,
                        'response': {'result': ejecutar_herramienta(tname, tinput)},
                    }
                })
            gemini_msgs.append({'role': 'user', 'parts': fn_responses})

        return "[Max iteraciones alcanzado]"

    # ── Modo autónomo ─────────────────────────────────────────────────────────

    def start_autonomous(self, on_msg: callable):
        if self._auto_running:
            return
        self._auto_running = True
        self._on_auto_msg  = on_msg
        threading.Thread(
            target=self._auto_loop, daemon=True, name='SentinelAria'
        ).start()

    def stop_autonomous(self):
        self._auto_running = False

    def _auto_loop(self):
        time.sleep(15)
        while self._auto_running:
            try:
                self._config = db.get_agent_config()
                if self.is_configured() and self.autonomy in ('semi', 'auto'):
                    snap = MonitorService.get().snapshot()
                    if snap['risk_score'] >= 70:
                        self._auto_analyze(snap)
            except Exception:
                pass
            time.sleep(60)

    def _auto_analyze(self, snap: dict):
        risk = snap['risk_score']
        if self._on_auto_msg:
            self._on_auto_msg(
                f"[Aria Autonoma] Riesgo {risk}/100 detectado. Investigando..."
            )

        puede_resolver = self.autonomy in ('semi', 'auto')
        puede_terminar = self.autonomy == 'auto'

        prompt = (
            f"ANALISIS AUTONOMO — Riesgo del sistema: {risk}/100\n"
            f"CPU: {snap['cpu']:.1f}% | RAM: {snap['ram']:.1f}% | "
            f"Alertas abiertas: {snap['open_alerts']}\n\n"
            f"Investiga el estado de seguridad usando las herramientas disponibles.\n"
        )
        if puede_resolver:
            prompt += "Puedes resolver alertas que sean claramente falsos positivos.\n"
        if puede_terminar:
            prompt += "Puedes terminar procesos SOLO si hay evidencia clara de malware (nombre sospechoso + ruta temp).\n"
        prompt += "Genera un informe conciso de lo que encontraste y las acciones tomadas."

        messages = [{'role': 'user', 'content': prompt}]

        def on_tool(name, _):
            if self._on_auto_msg:
                self._on_auto_msg(f"  → {name}")

        try:
            result = self._dispatch(messages, on_tool)
            if self._on_auto_msg:
                self._on_auto_msg(f"[Informe Aria]\n{result}")
        except Exception:
            pass
