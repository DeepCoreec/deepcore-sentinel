import customtkinter as ctk
from tkinter import ttk
import psutil
from theme import C, SEVERITY_COLOR, SEVERITY_LABEL


class ProcesosPanel(ctk.CTkFrame):
    def __init__(self, master, monitor, **kw):
        super().__init__(master, fg_color=C['base'], **kw)
        self.monitor = monitor
        self._build()
        self._refresh()

    def _build(self):
        # ── Topbar del panel ─────────────────────────────────────────────────
        top = ctk.CTkFrame(self, fg_color=C['mantle'],
                           border_width=1, border_color=C['surface1'],
                           corner_radius=0)
        top.pack(fill='x', padx=0, pady=0)

        ctk.CTkLabel(top, text='Monitor de Procesos',
                     font=ctk.CTkFont(size=18, weight='bold'),
                     text_color=C['text']).pack(side='left', padx=20, pady=14)

        ctk.CTkLabel(top, text='Proceso seleccionado:',
                     font=ctk.CTkFont(size=11), text_color=C['overlay0']).pack(
                         side='right', padx=(0, 8), pady=14)

        self._btn_kill = ctk.CTkButton(
            top, text='Terminar proceso', width=150, height=32,
            corner_radius=8, fg_color='transparent',
            border_width=1, border_color=C['red'],
            text_color=C['red'], hover_color=C['red'],
            font=ctk.CTkFont(size=12),
            command=self._kill_selected)
        self._btn_kill.pack(side='right', padx=8, pady=10)

        # ── Filtro búsqueda ───────────────────────────────────────────────────
        filter_row = ctk.CTkFrame(self, fg_color='transparent')
        filter_row.pack(fill='x', padx=20, pady=(12, 6))

        self._search = ctk.CTkEntry(
            filter_row, placeholder_text='Buscar proceso...',
            height=34, corner_radius=8, width=280,
            fg_color=C['surface0'], border_color=C['surface2'],
            text_color=C['text'], placeholder_text_color=C['overlay0'])
        self._search.pack(side='left')
        self._search.bind('<KeyRelease>', lambda _: self._apply_filter())

        self._lbl_count = ctk.CTkLabel(
            filter_row, text='', font=ctk.CTkFont(size=11),
            text_color=C['overlay0'])
        self._lbl_count.pack(side='left', padx=16)

        # ── Leyenda ────────────────────────────────────────────────────────────
        legend = ctk.CTkFrame(filter_row, fg_color='transparent')
        legend.pack(side='right')
        for label, color in [('Normal', C['subtext']), ('Medio', C['yellow']),
                              ('Alto', C['orange']), ('Critico', C['red'])]:
            ctk.CTkFrame(legend, fg_color=color, width=8, height=8,
                         corner_radius=4).pack(side='left', padx=(8,2))
            ctk.CTkLabel(legend, text=label, font=ctk.CTkFont(size=10),
                         text_color=C['subtext']).pack(side='left')

        # ── Tabla ──────────────────────────────────────────────────────────────
        table_frame = ctk.CTkFrame(self, fg_color=C['surface0'],
                                   border_width=1, border_color=C['surface1'],
                                   corner_radius=12)
        table_frame.pack(fill='both', expand=True, padx=20, pady=(0, 20))

        style = ttk.Style()
        style.theme_use('clam')
        style.configure('Sentinel.Treeview',
            background=C['surface0'],
            foreground=C['text'],
            fieldbackground=C['surface0'],
            rowheight=26,
            borderwidth=0,
            font=('Segoe UI', 10))
        style.configure('Sentinel.Treeview.Heading',
            background=C['mantle'],
            foreground=C['blue'],
            font=('Segoe UI', 10, 'bold'),
            relief='flat')
        style.map('Sentinel.Treeview',
            background=[('selected', C['surface1'])],
            foreground=[('selected', C['text'])])

        cols = ('pid', 'name', 'cpu', 'ram', 'user', 'status', 'riesgo')
        self._tree = ttk.Treeview(table_frame, columns=cols,
                                   show='headings', style='Sentinel.Treeview')

        widths = {'pid': 60, 'name': 200, 'cpu': 70, 'ram': 70,
                  'user': 140, 'status': 90, 'riesgo': 80}
        heads  = {'pid': 'PID', 'name': 'Nombre', 'cpu': 'CPU %',
                  'ram': 'RAM %', 'user': 'Usuario',
                  'status': 'Estado', 'riesgo': 'Riesgo'}

        for col in cols:
            self._tree.heading(col, text=heads[col],
                               command=lambda c=col: self._sort(c))
            self._tree.column(col, width=widths[col], anchor='center')
        self._tree.column('name', anchor='w')

        # Tags de color por riesgo
        self._tree.tag_configure('r0', foreground=C['text'])
        self._tree.tag_configure('r2', foreground=C['yellow'])
        self._tree.tag_configure('r3', foreground=C['orange'])
        self._tree.tag_configure('r4', foreground=C['red'])

        sb = ttk.Scrollbar(table_frame, orient='vertical',
                           command=self._tree.yview)
        self._tree.configure(yscrollcommand=sb.set)

        self._tree.pack(side='left', fill='both', expand=True, padx=2, pady=2)
        sb.pack(side='right', fill='y')

        self._all_procs = []
        self._sort_col  = 'cpu'
        self._sort_rev  = True

    def _refresh(self):
        snap = self.monitor.snapshot()
        self._all_procs = snap['processes']
        self._apply_filter()
        self.after(4000, self._refresh)

    def _apply_filter(self):
        query = self._search.get().lower().strip()
        filtered = [p for p in self._all_procs
                    if query in p['name'].lower() or query in str(p['pid'])]

        # Orden
        try:
            filtered = sorted(filtered,
                              key=lambda x: x.get(self._sort_col, 0),
                              reverse=self._sort_rev)
        except Exception:
            pass

        self._tree.delete(*self._tree.get_children())
        for p in filtered:
            tag = f'r{p["risk"]}' if p['risk'] in (2,3,4) else 'r0'
            risk_txt = SEVERITY_LABEL.get(p['risk'], 'Info')
            self._tree.insert('', 'end', iid=str(p['pid']),
                              values=(p['pid'], p['name'], f'{p["cpu"]:.1f}',
                                      f'{p["ram"]:.1f}', p['user'][:22],
                                      p['status'], risk_txt),
                              tags=(tag,))

        self._lbl_count.configure(text=f'{len(filtered)} procesos')

    def _sort(self, col: str):
        key_map = {'pid':'pid','name':'name','cpu':'cpu','ram':'ram',
                   'user':'user','status':'status','riesgo':'risk'}
        self._sort_col = key_map.get(col, col)
        self._sort_rev = not self._sort_rev
        self._apply_filter()

    def _kill_selected(self):
        sel = self._tree.selection()
        if not sel:
            return
        pid = int(sel[0])
        try:
            proc = psutil.Process(pid)
            name = proc.name()
            dlg = ctk.CTkToplevel(self)
            dlg.title('Confirmar')
            dlg.geometry('360x160')
            dlg.configure(fg_color=C['base'])
            dlg.grab_set()
            dlg.resizable(False, False)
            ctk.CTkFrame(dlg, fg_color=C['red'], height=3).pack(fill='x')
            ctk.CTkLabel(dlg, text=f'Terminar "{name}" (PID {pid})?',
                         font=ctk.CTkFont(size=13),
                         text_color=C['text']).pack(pady=24)
            btns = ctk.CTkFrame(dlg, fg_color='transparent')
            btns.pack()

            def confirm():
                try:
                    psutil.Process(pid).terminate()
                except Exception:
                    pass
                dlg.destroy()

            ctk.CTkButton(btns, text='Cancelar', width=110, height=36,
                          fg_color=C['surface1'], hover_color=C['surface2'],
                          text_color=C['text'], command=dlg.destroy).pack(
                              side='left', padx=8)
            ctk.CTkButton(btns, text='Terminar', width=110, height=36,
                          fg_color='transparent', border_width=1,
                          border_color=C['red'], text_color=C['red'],
                          hover_color=C['red'], command=confirm).pack(
                              side='left', padx=8)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass

    def cargar(self):
        self._refresh()
