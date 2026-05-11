import customtkinter as ctk
from tkinter import ttk
from theme import C

_SUSPICIOUS_PORTS = {4444,4445,5555,1337,31337,6666,6667,6668,6669,9001,9030,8888,7777}


class RedPanel(ctk.CTkFrame):
    def __init__(self, master, monitor, **kw):
        super().__init__(master, fg_color=C['base'], **kw)
        self.monitor = monitor
        self._build()
        self._refresh()

    def _build(self):
        top = ctk.CTkFrame(self, fg_color=C['mantle'],
                           border_width=1, border_color=C['surface1'],
                           corner_radius=0)
        top.pack(fill='x')

        ctk.CTkLabel(top, text='Monitoreo de Red',
                     font=ctk.CTkFont(size=18, weight='bold'),
                     text_color=C['text']).pack(side='left', padx=20, pady=14)

        self._lbl_total = ctk.CTkLabel(top, text='',
                                       font=ctk.CTkFont(size=11),
                                       text_color=C['overlay0'])
        self._lbl_total.pack(side='right', padx=20)

        # ── Stats de conexión ─────────────────────────────────────────────────
        stats_row = ctk.CTkFrame(self, fg_color='transparent')
        stats_row.pack(fill='x', padx=20, pady=(12,8))
        stats_row.columnconfigure((0,1,2,3), weight=1)

        self._stat_est  = self._stat_card(stats_row, 'Establecidas', '0', C['green'],  0)
        self._stat_escl = self._stat_card(stats_row, 'Escuchando',   '0', C['blue'],   1)
        self._stat_tw   = self._stat_card(stats_row, 'TIME_WAIT',    '0', C['yellow'], 2)
        self._stat_susp = self._stat_card(stats_row, 'Sospechosas',  '0', C['red'],    3)

        # ── Tabla ──────────────────────────────────────────────────────────────
        table_frame = ctk.CTkFrame(self, fg_color=C['surface0'],
                                   border_width=1, border_color=C['surface1'],
                                   corner_radius=12)
        table_frame.pack(fill='both', expand=True, padx=20, pady=(0,20))

        style = ttk.Style()
        style.configure('Net.Treeview',
            background=C['surface0'], foreground=C['text'],
            fieldbackground=C['surface0'], rowheight=24,
            borderwidth=0, font=('Segoe UI', 10))
        style.configure('Net.Treeview.Heading',
            background=C['mantle'], foreground=C['blue'],
            font=('Segoe UI', 10, 'bold'), relief='flat')
        style.map('Net.Treeview',
            background=[('selected', C['surface1'])],
            foreground=[('selected', C['text'])])

        cols = ('local', 'remote', 'remote_ip', 'port', 'status', 'pid', 'alerta')
        heads = {'local':'Local', 'remote':'Remoto', 'remote_ip':'IP Remota',
                 'port':'Puerto', 'status':'Estado', 'pid':'PID', 'alerta':'Alerta'}
        widths = {'local':160,'remote':180,'remote_ip':130,'port':70,
                  'status':110,'pid':60,'alerta':90}

        self._tree = ttk.Treeview(table_frame, columns=cols,
                                   show='headings', style='Net.Treeview')
        for col in cols:
            self._tree.heading(col, text=heads[col])
            self._tree.column(col, width=widths[col], anchor='center')
        self._tree.column('local',  anchor='w')
        self._tree.column('remote', anchor='w')

        self._tree.tag_configure('normal',    foreground=C['text'])
        self._tree.tag_configure('suspicious',foreground=C['red'])

        sb = ttk.Scrollbar(table_frame, orient='vertical',
                           command=self._tree.yview)
        self._tree.configure(yscrollcommand=sb.set)
        self._tree.pack(side='left', fill='both', expand=True, padx=2, pady=2)
        sb.pack(side='right', fill='y')

    def _stat_card(self, parent, label, value, color, col):
        card = ctk.CTkFrame(parent, fg_color=C['surface0'],
                            border_width=1, border_color=C['surface1'],
                            corner_radius=10)
        card.grid(row=0, column=col, sticky='nsew',
                  padx=(0 if col == 0 else 4, 4 if col < 3 else 0), ipady=8)
        lbl = ctk.CTkLabel(card, text=value,
                           font=ctk.CTkFont(size=22, weight='bold'),
                           text_color=color)
        lbl.pack(pady=(10,2))
        ctk.CTkLabel(card, text=label, font=ctk.CTkFont(size=10),
                     text_color=C['subtext']).pack(pady=(0,8))
        return lbl

    def _refresh(self):
        snap = self.monitor.snapshot()
        conns = snap['connections']

        est   = sum(1 for c in conns if c['status'] == 'ESTABLISHED')
        escl  = sum(1 for c in conns if c['status'] == 'LISTEN')
        tw    = sum(1 for c in conns if c['status'] == 'TIME_WAIT')
        susp  = sum(1 for c in conns if c['risk'] > 0)

        self._stat_est.configure(text=str(est))
        self._stat_escl.configure(text=str(escl))
        self._stat_tw.configure(text=str(tw))
        self._stat_susp.configure(text=str(susp))
        self._lbl_total.configure(text=f'{len(conns)} conexiones activas')

        self._tree.delete(*self._tree.get_children())
        for c in sorted(conns, key=lambda x: x['risk'], reverse=True):
            is_susp = c['risk'] > 0
            alerta  = 'Puerto sospechoso' if c['remote_port'] in _SUSPICIOUS_PORTS else ''
            tag = 'suspicious' if is_susp else 'normal'
            self._tree.insert('', 'end',
                              values=(c['local'], c['remote'], c['remote_ip'],
                                      c['remote_port'], c['status'],
                                      c['pid'], alerta),
                              tags=(tag,))

        self.after(5000, self._refresh)

    def cargar(self):
        self._refresh()
