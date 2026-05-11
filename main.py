import customtkinter as ctk
import threading, sys, os
import theme
import database as db
from monitor import MonitorService

theme.apply()


class SentinelApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title('DeepCore Sentinel')
        self.geometry('1280x760')
        self.minsize(1000, 640)
        self.configure(fg_color=theme.C['base'])

        # ── Icono ──────────────────────────────────────────────────────────────
        try:
            icon_path = os.path.join(
                getattr(sys, '_MEIPASS', os.path.dirname(__file__)), 'icon.ico')
            if os.path.exists(icon_path):
                self.iconbitmap(icon_path)
        except Exception:
            pass

        db.init_db()
        self._monitor = MonitorService.get()
        self._monitor.start()

        self._panels     = {}
        self._active_nav = None

        self._build_topbar()
        self._build_body()
        self._nav_to('dashboard')
        self._update_topbar()

    # ── Topbar ─────────────────────────────────────────────────────────────────

    def _build_topbar(self):
        tb = ctk.CTkFrame(self, fg_color=theme.C['mantle'],
                          height=58, corner_radius=0)
        tb.pack(side='top', fill='x')
        tb.pack_propagate(False)

        # Separador inferior
        ctk.CTkFrame(tb, fg_color=theme.C['surface1'],
                     height=1).place(relx=0, rely=1.0, relwidth=1.0, anchor='sw')

        # Badge DC
        badge = ctk.CTkFrame(tb, fg_color=theme.C['sentinel'],
                             width=38, height=30, corner_radius=8)
        badge.place(x=16, rely=0.5, anchor='w')
        badge.pack_propagate(False)
        ctk.CTkLabel(badge, text='DC', font=ctk.CTkFont(size=13, weight='bold'),
                     text_color='#fff').place(relx=0.5, rely=0.5, anchor='center')

        ctk.CTkLabel(tb, text='DeepCore Sentinel',
                     font=ctk.CTkFont(size=17, weight='bold'),
                     text_color=theme.C['text']).place(x=64, rely=0.5, anchor='w')

        # Etiqueta de seguridad
        sec_badge = ctk.CTkFrame(tb, fg_color='#0d1f0d',
                                 border_width=1,
                                 border_color=theme.C['green'],
                                 corner_radius=6)
        sec_badge.place(x=264, rely=0.5, anchor='w')
        ctk.CTkLabel(sec_badge, text='PROTECCION ACTIVA',
                     font=ctk.CTkFont(size=9, weight='bold'),
                     text_color=theme.C['green']).pack(padx=8, pady=3)

        # Score de riesgo (derecha)
        risk_f = ctk.CTkFrame(tb, fg_color=theme.C['surface0'],
                              corner_radius=8)
        risk_f.place(relx=1.0, x=-16, rely=0.5, anchor='e')

        ctk.CTkLabel(risk_f, text='RIESGO',
                     font=ctk.CTkFont(size=8, weight='bold'),
                     text_color=theme.C['overlay0']).pack(padx=10, pady=(4,0))
        self._risk_lbl = ctk.CTkLabel(risk_f, text='0',
                                       font=ctk.CTkFont(size=20, weight='bold'),
                                       text_color=theme.C['green'])
        self._risk_lbl.pack(padx=10, pady=(0,4))

        # Alertas abiertas
        alert_f = ctk.CTkFrame(tb, fg_color=theme.C['surface0'],
                               corner_radius=8)
        alert_f.place(relx=1.0, x=-120, rely=0.5, anchor='e')
        ctk.CTkLabel(alert_f, text='ALERTAS',
                     font=ctk.CTkFont(size=8, weight='bold'),
                     text_color=theme.C['overlay0']).pack(padx=10, pady=(4,0))
        self._alerts_lbl = ctk.CTkLabel(alert_f, text='0',
                                         font=ctk.CTkFont(size=20, weight='bold'),
                                         text_color=theme.C['yellow'])
        self._alerts_lbl.pack(padx=10, pady=(0,4))

    def _update_topbar(self):
        snap  = self._monitor.snapshot()
        risk  = snap['risk_score']
        color = (theme.C['green']  if risk < 30 else
                 theme.C['yellow'] if risk < 60 else
                 theme.C['red'])
        self._risk_lbl.configure(text=str(risk), text_color=color)
        self._alerts_lbl.configure(text=str(snap['open_alerts']))
        self.after(3000, self._update_topbar)

    # ── Body: sidebar + contenido ──────────────────────────────────────────────

    def _build_body(self):
        body = ctk.CTkFrame(self, fg_color=theme.C['base'], corner_radius=0)
        body.pack(fill='both', expand=True)

        # Sidebar
        sidebar = ctk.CTkFrame(body, fg_color=theme.C['mantle'],
                               width=210, corner_radius=0)
        sidebar.pack(side='left', fill='y')
        sidebar.pack_propagate(False)

        # Separador derecho
        ctk.CTkFrame(body, fg_color=theme.C['surface1'],
                     width=1).pack(side='left', fill='y')

        # Contenido
        self._content = ctk.CTkFrame(body, fg_color=theme.C['base'],
                                     corner_radius=0)
        self._content.pack(side='left', fill='both', expand=True)

        self._build_sidebar(sidebar)

    def _build_sidebar(self, sidebar):
        ctk.CTkLabel(sidebar, text='NAVEGACION',
                     font=ctk.CTkFont(size=9, weight='bold'),
                     text_color=theme.C['overlay0']).pack(
                         anchor='w', padx=20, pady=(22, 10))

        self._nav_btns = {}
        nav_items = [
            ('dashboard', 'Dashboard'),
            ('procesos',  'Procesos'),
            ('red',       'Red'),
            ('archivos',  'Archivos'),
            ('alertas',   'Alertas'),
            ('reportes',  'Reportes'),
            ('agente',    'Agente IA'),
        ]

        for key, label in nav_items:
            btn = ctk.CTkButton(
                sidebar, text=label, anchor='w',
                height=40, corner_radius=8,
                fg_color='transparent', hover_color=theme.C['surface0'],
                text_color=theme.C['subtext'],
                font=ctk.CTkFont(size=13),
                command=lambda k=key: self._nav_to(k))
            btn.pack(fill='x', padx=10, pady=2)
            self._nav_btns[key] = btn

        # Separador
        ctk.CTkFrame(sidebar, fg_color=theme.C['surface1'],
                     height=1).pack(fill='x', padx=16, pady=16)

        # Status
        ctk.CTkLabel(sidebar, text='ESTADO',
                     font=ctk.CTkFont(size=9, weight='bold'),
                     text_color=theme.C['overlay0']).pack(
                         anchor='w', padx=20, pady=(0, 8))

        status_f = ctk.CTkFrame(sidebar, fg_color=theme.C['surface0'],
                                corner_radius=8)
        status_f.pack(fill='x', padx=10, pady=(0, 8))

        dot_row = ctk.CTkFrame(status_f, fg_color='transparent')
        dot_row.pack(anchor='w', padx=12, pady=8)
        ctk.CTkFrame(dot_row, fg_color=theme.C['green'],
                     width=8, height=8, corner_radius=4).pack(side='left')
        ctk.CTkLabel(dot_row, text='  Monitor activo',
                     font=ctk.CTkFont(size=11),
                     text_color=theme.C['text']).pack(side='left')

        # Versión
        ctk.CTkLabel(sidebar, text='v1.0.0',
                     font=ctk.CTkFont(size=9),
                     text_color=theme.C['overlay0']).pack(
                         side='bottom', pady=14)

        ctk.CTkLabel(sidebar, text='deepcore.ec',
                     font=ctk.CTkFont(size=9),
                     text_color=theme.C['overlay0']).pack(side='bottom')

    # ── Navegación ─────────────────────────────────────────────────────────────

    def _nav_to(self, key: str):
        if self._active_nav == key:
            return

        # Resetear botones
        for k, btn in self._nav_btns.items():
            if k == key:
                btn.configure(fg_color=theme.C['surface0'],
                               text_color=theme.C['blue'],
                               font=ctk.CTkFont(size=13, weight='bold'))
            else:
                btn.configure(fg_color='transparent',
                               text_color=theme.C['subtext'],
                               font=ctk.CTkFont(size=13))

        # Ocultar panel actual
        if self._active_nav and self._active_nav in self._panels:
            self._panels[self._active_nav].pack_forget()

        self._active_nav = key

        # Crear o mostrar panel
        if key not in self._panels:
            self._panels[key] = self._create_panel(key)

        self._panels[key].pack(fill='both', expand=True)

        # Refrescar datos si el panel lo soporta
        panel = self._panels[key]
        if hasattr(panel, 'cargar'):
            panel.cargar()

    def _create_panel(self, key: str):
        parent = self._content
        if key == 'dashboard':
            from modules.dashboard import DashboardPanel
            return DashboardPanel(parent, self._monitor)
        elif key == 'procesos':
            from modules.procesos import ProcesosPanel
            return ProcesosPanel(parent, self._monitor)
        elif key == 'red':
            from modules.red import RedPanel
            return RedPanel(parent, self._monitor)
        elif key == 'archivos':
            from modules.archivos import ArchivosPanel
            return ArchivosPanel(parent)
        elif key == 'alertas':
            from modules.alertas import AlertasPanel
            return AlertasPanel(parent)
        elif key == 'reportes':
            from modules.reportes import ReportesPanel
            return ReportesPanel(parent, self._monitor)
        elif key == 'agente':
            from modules.agente import AgentPanel
            return AgentPanel(parent, self._monitor)

    # ── Cierre limpio ──────────────────────────────────────────────────────────

    def on_close(self):
        self._monitor.stop()
        self.destroy()


def check_license_and_start():
    root = ctk.CTk()
    root.withdraw()

    import json, os
    cfg_dir = os.path.join(os.environ.get('APPDATA', ''), 'DeepCoreSentinel')
    os.makedirs(cfg_dir, exist_ok=True)
    cfg_path = os.path.join(cfg_dir, 'license.json')

    def launch():
        root.destroy()
        app = SentinelApp()
        app.protocol('WM_DELETE_WINDOW', app.on_close)
        app.mainloop()

    # Verificar si ya existe licencia guardada
    if os.path.exists(cfg_path):
        try:
            with open(cfg_path) as f:
                data = json.load(f)
            clave = data.get('clave', '')
            if clave:
                from modules.licencia import verificar_licencia
                result = verificar_licencia(clave)
                if result.get('valida'):
                    launch()
                    return
        except Exception:
            pass

    # Mostrar ventana de licencia
    from modules.licencia import VentanaLicencia

    def on_success():
        # Pedir la clave otra vez para guardarla (simplificado)
        launch()

    splash = ctk.CTkToplevel(root)
    splash.withdraw()
    root.after(100, lambda: splash.withdraw())

    from modules.licencia import VentanaLicencia
    win = VentanaLicencia(root, on_success)
    root.mainloop()


if __name__ == '__main__':
    # En desarrollo — lanzar directamente sin verificación de licencia
    import os
    DEV_MODE = not getattr(sys, 'frozen', False)

    if DEV_MODE:
        db.init_db()
        app = SentinelApp()
        app.protocol('WM_DELETE_WINDOW', app.on_close)
        app.mainloop()
    else:
        check_license_and_start()
