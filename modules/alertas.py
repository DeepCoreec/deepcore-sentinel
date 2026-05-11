import customtkinter as ctk
from tkinter import ttk
from theme import C, SEVERITY_COLOR, SEVERITY_LABEL
import database as db


class AlertasPanel(ctk.CTkFrame):
    def __init__(self, master, **kw):
        super().__init__(master, fg_color=C['base'], **kw)
        self._filter_status = 'open'
        self._filter_sev    = -1         # -1 = todos
        self._build()
        self._refresh()

    def _build(self):
        top = ctk.CTkFrame(self, fg_color=C['mantle'],
                           border_width=1, border_color=C['surface1'],
                           corner_radius=0)
        top.pack(fill='x')

        ctk.CTkLabel(top, text='Centro de Alertas',
                     font=ctk.CTkFont(size=18, weight='bold'),
                     text_color=C['text']).pack(side='left', padx=20, pady=14)

        self._lbl_count = ctk.CTkLabel(top, text='',
                                       font=ctk.CTkFont(size=11),
                                       text_color=C['overlay0'])
        self._lbl_count.pack(side='right', padx=20)

        # ── Filtros ────────────────────────────────────────────────────────────
        filter_row = ctk.CTkFrame(self, fg_color='transparent')
        filter_row.pack(fill='x', padx=20, pady=(12,8))

        ctk.CTkLabel(filter_row, text='Estado:',
                     font=ctk.CTkFont(size=11), text_color=C['subtext']).pack(
                         side='left', padx=(0,6))

        for label, val in [('Abiertas', 'open'), ('Resueltas', 'resolved'),
                           ('Falsas', 'false_positive'), ('Todas', None)]:
            ctk.CTkButton(filter_row, text=label, width=90, height=28,
                          corner_radius=20, font=ctk.CTkFont(size=11),
                          fg_color=C['surface1'], hover_color=C['surface2'],
                          text_color=C['text'],
                          command=lambda v=val: self._set_status(v)).pack(
                              side='left', padx=3)

        ctk.CTkFrame(filter_row, fg_color=C['surface2'],
                     width=1).pack(side='left', fill='y', padx=12, pady=4)

        ctk.CTkLabel(filter_row, text='Severidad:',
                     font=ctk.CTkFont(size=11), text_color=C['subtext']).pack(
                         side='left', padx=(0,6))

        for sev, label in [(-1,'Todas'),(4,'Critica'),(3,'Alta'),(2,'Media'),(1,'Baja')]:
            color = SEVERITY_COLOR.get(sev, C['subtext']) if sev >= 0 else C['subtext']
            ctk.CTkButton(filter_row, text=label, width=80, height=28,
                          corner_radius=20, font=ctk.CTkFont(size=11),
                          fg_color=C['surface1'], hover_color=C['surface2'],
                          text_color=color,
                          command=lambda s=sev: self._set_sev(s)).pack(
                              side='left', padx=3)

        # ── Acciones ────────────────────────────────────────────────────────────
        action_row = ctk.CTkFrame(self, fg_color='transparent')
        action_row.pack(fill='x', padx=20, pady=(0,8))

        ctk.CTkButton(action_row, text='Marcar como resuelta',
                      height=32, width=170, corner_radius=8,
                      fg_color=C['green'], hover_color=C['teal'],
                      text_color='#000', font=ctk.CTkFont(size=12, weight='bold'),
                      command=lambda: self._set_selected_status('resolved')).pack(
                          side='left', padx=(0,8))

        ctk.CTkButton(action_row, text='Falsa alarma',
                      height=32, width=130, corner_radius=8,
                      fg_color='transparent', border_width=1,
                      border_color=C['overlay0'], text_color=C['subtext'],
                      command=lambda: self._set_selected_status('false_positive')).pack(
                          side='left', padx=(0,8))

        ctk.CTkButton(action_row, text='Reabrir',
                      height=32, width=100, corner_radius=8,
                      fg_color='transparent', border_width=1,
                      border_color=C['blue'], text_color=C['blue'],
                      command=lambda: self._set_selected_status('open')).pack(
                          side='left')

        # ── Tabla ──────────────────────────────────────────────────────────────
        table_frame = ctk.CTkFrame(self, fg_color=C['surface0'],
                                   border_width=1, border_color=C['surface1'],
                                   corner_radius=12)
        table_frame.pack(fill='both', expand=True, padx=20, pady=(0,20))

        style = ttk.Style()
        style.configure('Alert.Treeview',
            background=C['surface0'], foreground=C['text'],
            fieldbackground=C['surface0'], rowheight=26,
            borderwidth=0, font=('Segoe UI', 10))
        style.configure('Alert.Treeview.Heading',
            background=C['mantle'], foreground=C['blue'],
            font=('Segoe UI', 10, 'bold'), relief='flat')
        style.map('Alert.Treeview',
            background=[('selected', C['surface1'])],
            foreground=[('selected', C['text'])])

        cols = ('id', 'ts', 'sev', 'categoria', 'titulo', 'estado')
        heads = {'id':'#', 'ts':'Fecha/Hora', 'sev':'Severidad',
                 'categoria':'Categoría', 'titulo':'Alerta', 'estado':'Estado'}
        widths = {'id':40, 'ts':130, 'sev':90, 'categoria':90,
                  'titulo':350, 'estado':90}

        self._tree = ttk.Treeview(table_frame, columns=cols,
                                   show='headings', style='Alert.Treeview',
                                   selectmode='extended')
        for col in cols:
            self._tree.heading(col, text=heads[col])
            self._tree.column(col, width=widths[col],
                              anchor='center' if col not in ('titulo',) else 'w')

        for sev, color in SEVERITY_COLOR.items():
            self._tree.tag_configure(f's{sev}', foreground=color)
        self._tree.tag_configure('resolved',       foreground=C['overlay0'])
        self._tree.tag_configure('false_positive',  foreground=C['surface2'])

        sb = ttk.Scrollbar(table_frame, orient='vertical',
                           command=self._tree.yview)
        self._tree.configure(yscrollcommand=sb.set)
        self._tree.pack(side='left', fill='both', expand=True, padx=2, pady=2)
        sb.pack(side='right', fill='y')

    def _set_status(self, status):
        self._filter_status = status
        self._refresh()

    def _set_sev(self, sev):
        self._filter_sev = sev
        self._refresh()

    def _refresh(self):
        alerts = db.get_alerts(status=self._filter_status, limit=500)
        if self._filter_sev >= 0:
            alerts = [a for a in alerts if a['severity'] == self._filter_sev]

        self._tree.delete(*self._tree.get_children())
        for a in alerts:
            ts    = a['ts'][:19].replace('T', ' ')
            sev   = SEVERITY_LABEL.get(a['severity'], 'Info')
            tag   = a['status'] if a['status'] in ('resolved','false_positive') \
                    else f's{a["severity"]}'
            self._tree.insert('', 'end', iid=str(a['id']),
                              values=(a['id'], ts, sev, a['category'],
                                      a['title'], a['status']),
                              tags=(tag,))

        self._lbl_count.configure(text=f'{len(alerts)} alertas')
        self.after(8000, self._refresh)

    def _set_selected_status(self, status: str):
        for iid in self._tree.selection():
            db.update_alert_status(int(iid), status)
        self._refresh()

    def cargar(self):
        self._refresh()
