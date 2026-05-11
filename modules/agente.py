"""
Panel del Agente IA Aria — chat + configuración multi-proveedor.
"""
import customtkinter as ctk
import theme
import database as db
from modules.agent_engine import AgentEngine


class AgentPanel(ctk.CTkFrame):
    def __init__(self, parent, monitor):
        super().__init__(parent, fg_color=theme.C['base'], corner_radius=0)
        self._monitor        = monitor
        self._engine         = AgentEngine()
        self._history        = []
        self._config_visible = False

        self._build_ui()
        self._engine.start_autonomous(self._on_auto_msg)

    # ── Layout ────────────────────────────────────────────────────────────────

    def _build_ui(self):
        # Header
        header = ctk.CTkFrame(self, fg_color=theme.C['mantle'],
                              corner_radius=0, height=52)
        header.pack(fill='x')
        header.pack_propagate(False)

        ctk.CTkLabel(header, text='Agente IA — Aria',
                     font=ctk.CTkFont(size=16, weight='bold'),
                     text_color=theme.C['mauve']).pack(side='left', padx=20, pady=14)

        self._auto_lbl = ctk.CTkLabel(
            header, text='',
            font=ctk.CTkFont(size=10),
            text_color=theme.C['overlay0'])
        self._auto_lbl.pack(side='right', padx=20)

        ctk.CTkFrame(self, fg_color=theme.C['surface1'], height=1).pack(fill='x')

        # Botón para abrir/cerrar configuración
        self._btn_cfg = ctk.CTkButton(
            self, text='Configurar API Key  ▾',
            height=30, corner_radius=0,
            fg_color=theme.C['surface0'], hover_color=theme.C['surface1'],
            text_color=theme.C['subtext'], font=ctk.CTkFont(size=11),
            command=self._toggle_config
        )
        self._btn_cfg.pack(fill='x')

        # Panel de configuración (oculto al inicio)
        self._config_frame = ctk.CTkFrame(
            self, fg_color=theme.C['surface0'], corner_radius=0)
        self._build_config()

        # Área de chat
        self._chat_scroll = ctk.CTkScrollableFrame(
            self, fg_color=theme.C['base'], corner_radius=0)
        self._chat_scroll.pack(fill='both', expand=True)

        ctk.CTkFrame(self, fg_color=theme.C['surface1'], height=1).pack(fill='x')

        # Barra de input
        input_bar = ctk.CTkFrame(self, fg_color=theme.C['mantle'],
                                  corner_radius=0, height=62)
        input_bar.pack(fill='x')
        input_bar.pack_propagate(False)

        self._input = ctk.CTkEntry(
            input_bar,
            placeholder_text='Pregunta a Aria... (ej: ¿hay amenazas activas?)',
            height=38, corner_radius=8,
            fg_color=theme.C['surface0'],
            border_color=theme.C['surface2'], border_width=1,
            text_color=theme.C['text'],
            font=ctk.CTkFont(size=13)
        )
        self._input.pack(side='left', fill='x', expand=True, padx=(16, 8), pady=12)
        self._input.bind('<Return>',   lambda e: self._send())
        self._input.bind('<FocusIn>',  lambda e: self._input.configure(
            border_color=theme.C['mauve']))
        self._input.bind('<FocusOut>', lambda e: self._input.configure(
            border_color=theme.C['surface2']))

        self._send_btn = ctk.CTkButton(
            input_bar, text='Enviar', width=85, height=38,
            corner_radius=8,
            fg_color=theme.C['mauve'], hover_color=theme.C['lavender'],
            text_color='#000', font=ctk.CTkFont(size=13, weight='bold'),
            command=self._send
        )
        self._send_btn.pack(side='right', padx=(0, 16), pady=12)

        # Mensaje de bienvenida
        self._add_bubble('assistant',
            'Hola, soy Aria — tu agente de ciberseguridad. Puedo analizar procesos, '
            'conexiones de red, alertas y tomar acciones de protección en tiempo real.\n\n'
            'Configura tu API Key (Anthropic, OpenAI, Gemini, Kimi, DeepSeek, Groq, Mistral o Grok) para comenzar.'
        )
        self._update_auto_label()

    def _build_config(self):
        row1 = ctk.CTkFrame(self._config_frame, fg_color='transparent')
        row1.pack(fill='x', padx=16, pady=(14, 6))

        # Proveedor
        ctk.CTkLabel(row1, text='Proveedor:',
                     text_color=theme.C['subtext'],
                     font=ctk.CTkFont(size=11)).pack(side='left')
        self._prov_var = ctk.StringVar(value=self._engine.provider)
        ctk.CTkOptionMenu(
            row1, variable=self._prov_var,
            values=['anthropic', 'openai', 'gemini', 'kimi', 'deepseek', 'groq', 'mistral', 'grok'],
            width=130, height=32, corner_radius=6,
            fg_color=theme.C['surface1'], button_color=theme.C['surface2'],
            text_color=theme.C['text'], font=ctk.CTkFont(size=12),
            command=self._on_provider_change
        ).pack(side='left', padx=(8, 20))

        # Modelo
        ctk.CTkLabel(row1, text='Modelo:',
                     text_color=theme.C['subtext'],
                     font=ctk.CTkFont(size=11)).pack(side='left')
        self._model_var = ctk.StringVar(value=self._engine.model)
        self._model_menu = ctk.CTkOptionMenu(
            row1, variable=self._model_var,
            values=self._models_for(self._engine.provider),
            width=210, height=32, corner_radius=6,
            fg_color=theme.C['surface1'], button_color=theme.C['surface2'],
            text_color=theme.C['text'], font=ctk.CTkFont(size=12),
        )
        self._model_menu.pack(side='left', padx=8)

        row2 = ctk.CTkFrame(self._config_frame, fg_color='transparent')
        row2.pack(fill='x', padx=16, pady=(0, 6))

        # API Key
        ctk.CTkLabel(row2, text='API Key:',
                     text_color=theme.C['subtext'],
                     font=ctk.CTkFont(size=11)).pack(side='left')
        self._key_entry = ctk.CTkEntry(
            row2, show='*', height=32, width=340, corner_radius=6,
            fg_color=theme.C['surface1'],
            border_color=theme.C['surface2'], border_width=1,
            text_color=theme.C['text'], font=ctk.CTkFont(size=12)
        )
        self._key_entry.pack(side='left', padx=(8, 20))
        if self._engine.api_key:
            self._key_entry.insert(0, self._engine.api_key)

        # Autonomía
        ctk.CTkLabel(row2, text='Autonomia:',
                     text_color=theme.C['subtext'],
                     font=ctk.CTkFont(size=11)).pack(side='left')
        self._auto_var = ctk.StringVar(value=self._engine.autonomy)
        ctk.CTkOptionMenu(
            row2, variable=self._auto_var,
            values=['manual', 'semi', 'auto'],
            width=110, height=32, corner_radius=6,
            fg_color=theme.C['surface1'], button_color=theme.C['surface2'],
            text_color=theme.C['text'], font=ctk.CTkFont(size=12),
        ).pack(side='left', padx=8)

        row3 = ctk.CTkFrame(self._config_frame, fg_color='transparent')
        row3.pack(fill='x', padx=16, pady=(0, 14))

        ctk.CTkButton(
            row3, text='Guardar', width=90, height=30,
            corner_radius=6,
            fg_color=theme.C['green'], hover_color=theme.C['teal'],
            text_color='#000', font=ctk.CTkFont(size=12, weight='bold'),
            command=self._save_config
        ).pack(side='left')

        self._cfg_status = ctk.CTkLabel(
            row3, text='',
            font=ctk.CTkFont(size=11),
            text_color=theme.C['overlay0'])
        self._cfg_status.pack(side='left', padx=12)

        # Nota de autonomía
        ctk.CTkLabel(
            row3,
            text='manual=solo sugiere  |  semi=resuelve falsos positivos  |  auto=puede terminar procesos',
            font=ctk.CTkFont(size=9),
            text_color=theme.C['overlay0']
        ).pack(side='right', padx=8)

    # ── Config handlers ───────────────────────────────────────────────────────

    def _models_for(self, provider: str) -> list:
        return AgentEngine.PROVIDERS.get(provider, {}).get('models', [provider])

    def _on_provider_change(self, prov: str):
        models = self._models_for(prov)
        self._model_menu.configure(values=models)
        self._model_var.set(models[0] if models else '')

    def _toggle_config(self):
        if self._config_visible:
            self._config_frame.pack_forget()
            self._btn_cfg.configure(text='Configurar API Key  ▾')
        else:
            self._config_frame.pack(fill='x', before=self._chat_scroll)
            self._btn_cfg.configure(text='Configurar API Key  ▴')
        self._config_visible = not self._config_visible

    def _save_config(self):
        provider = self._prov_var.get()
        api_key  = self._key_entry.get().strip()
        model    = self._model_var.get()
        autonomy = self._auto_var.get()
        db.save_agent_config(provider, api_key, model, autonomy)
        self._engine.reload_config()
        self._cfg_status.configure(text='Configuracion guardada.', text_color=theme.C['green'])
        self.after(2500, lambda: self._cfg_status.configure(text=''))
        self._update_auto_label()

    def _update_auto_label(self):
        labels = {
            'manual': ('Modo manual',         theme.C['overlay0']),
            'semi':   ('Semi-automatico',      theme.C['yellow']),
            'auto':   ('Autonomia total activa', theme.C['green']),
        }
        text, color = labels.get(self._engine.autonomy, ('', theme.C['overlay0']))
        self._auto_lbl.configure(text=text, text_color=color)

    # ── Chat ──────────────────────────────────────────────────────────────────

    def _send(self):
        text = self._input.get().strip()
        if not text:
            return
        self._input.delete(0, 'end')
        self._add_bubble('user', text)
        self._history.append({'role': 'user', 'content': text})
        self._set_loading(True)

        self._engine.chat(
            list(self._history),
            on_tool  = self._on_tool_call,
            on_done  = self._on_done,
            on_error = self._on_error,
        )

    def _on_tool_call(self, name: str, _inputs: dict):
        self.after(0, lambda n=name: self._add_step(n))

    def _on_done(self, text: str):
        self._history.append({'role': 'assistant', 'content': text})
        self.after(0, lambda: self._set_loading(False))
        self.after(0, lambda t=text: self._add_bubble('assistant', t))

    def _on_error(self, err: str):
        self.after(0, lambda: self._set_loading(False))
        self.after(0, lambda e=err: self._add_bubble('error', f'Error: {e}'))

    def _on_auto_msg(self, text: str):
        self.after(0, lambda t=text: self._add_bubble('auto', t))

    # ── Burbujas de chat ──────────────────────────────────────────────────────

    def _add_bubble(self, role: str, text: str):
        p = self._chat_scroll

        if role == 'user':
            f = ctk.CTkFrame(p, fg_color=theme.C['surface1'], corner_radius=10)
            f.pack(anchor='e', padx=16, pady=(4, 2), fill='x')
            ctk.CTkLabel(f, text=text, wraplength=560, justify='left',
                          font=ctk.CTkFont(size=12),
                          text_color=theme.C['text']).pack(padx=14, pady=8, anchor='w')

        elif role == 'assistant':
            f = ctk.CTkFrame(p, fg_color=theme.C['surface0'], corner_radius=10,
                              border_width=1, border_color=theme.C['mauve'])
            f.pack(anchor='w', padx=16, pady=(2, 4), fill='x')

            inner = ctk.CTkFrame(f, fg_color='transparent')
            inner.pack(fill='x', padx=0)

            avatar = ctk.CTkFrame(inner, fg_color=theme.C['mauve'],
                                   width=24, height=24, corner_radius=12)
            avatar.pack(side='left', padx=(12, 8), pady=10, anchor='n')
            avatar.pack_propagate(False)
            ctk.CTkLabel(avatar, text='A',
                          font=ctk.CTkFont(size=10, weight='bold'),
                          text_color='#fff').place(relx=0.5, rely=0.5, anchor='center')

            ctk.CTkLabel(inner, text=text, wraplength=530, justify='left',
                          font=ctk.CTkFont(size=12),
                          text_color=theme.C['text']).pack(
                              side='left', padx=(0, 14), pady=10)

        elif role == 'auto':
            f = ctk.CTkFrame(p, fg_color='#060f14', corner_radius=8,
                              border_width=1, border_color=theme.C['teal'])
            f.pack(anchor='w', padx=16, pady=2, fill='x')
            ctk.CTkLabel(f, text=text, wraplength=560, justify='left',
                          font=ctk.CTkFont(size=11),
                          text_color=theme.C['teal']).pack(padx=12, pady=6, anchor='w')

        elif role == 'error':
            f = ctk.CTkFrame(p, fg_color='#140606', corner_radius=8,
                              border_width=1, border_color=theme.C['red'])
            f.pack(anchor='w', padx=16, pady=2, fill='x')
            ctk.CTkLabel(f, text=text, wraplength=560, justify='left',
                          font=ctk.CTkFont(size=11),
                          text_color=theme.C['red']).pack(padx=12, pady=6, anchor='w')

        self.after(80, lambda: self._chat_scroll._parent_canvas.yview_moveto(1.0))

    def _add_step(self, tool_name: str):
        f = ctk.CTkFrame(self._chat_scroll, fg_color='transparent')
        f.pack(anchor='w', padx=36, pady=1)
        ctk.CTkLabel(f, text=f'  → {tool_name}',
                      font=ctk.CTkFont(size=10),
                      text_color=theme.C['overlay0']).pack(side='left')

    def _set_loading(self, loading: bool):
        state = 'disabled' if loading else 'normal'
        self._send_btn.configure(
            state=state, text=('Procesando...' if loading else 'Enviar'))
        self._input.configure(state=state)
