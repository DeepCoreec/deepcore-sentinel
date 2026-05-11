import customtkinter as ctk
import matplotlib
matplotlib.use('TkAgg')
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.pyplot as plt
from theme import C, SEVERITY_COLOR, SEVERITY_LABEL
import database as db

plt.style.use('dark_background')
_BG  = C['surface0']
_AX  = C['base']


def _hex_to_rgb01(h: str):
    h = h.lstrip('#')
    return tuple(int(h[i:i+2], 16)/255 for i in (0,2,4))


class DashboardPanel(ctk.CTkFrame):
    def __init__(self, master, monitor, **kw):
        super().__init__(master, fg_color=C['base'], **kw)
        self.monitor = monitor
        self._figures = []
        self._build()
        self._refresh()

    def _build(self):
        # ── Fila de KPI ──────────────────────────────────────────────────────
        kpi_row = ctk.CTkFrame(self, fg_color='transparent')
        kpi_row.pack(fill='x', padx=20, pady=(16, 8))
        kpi_row.columnconfigure((0,1,2,3,4), weight=1)

        self._kpi_cpu   = self._kpi(kpi_row, 'CPU',     '0%',  C['blue'],    0)
        self._kpi_ram   = self._kpi(kpi_row, 'RAM',     '0%',  C['mauve'],   1)
        self._kpi_disk  = self._kpi(kpi_row, 'Disco',   '0%',  C['teal'],    2)
        self._kpi_net   = self._kpi(kpi_row, 'Red',     '0 KB/s', C['green'],3)
        self._kpi_risk  = self._kpi(kpi_row, 'Riesgo',  '0',   C['red'],     4)

        # ── Fila de gráficas ─────────────────────────────────────────────────
        charts_row = ctk.CTkFrame(self, fg_color='transparent')
        charts_row.pack(fill='both', expand=True, padx=20, pady=(0, 8))
        charts_row.columnconfigure((0,1), weight=1)
        charts_row.rowconfigure(0, weight=1)

        self._fig_cpu, self._ax_cpu, self._canvas_cpu = \
            self._make_chart(charts_row, 'CPU %', C['blue'], 0, 0)
        self._fig_ram, self._ax_ram, self._canvas_ram = \
            self._make_chart(charts_row, 'RAM %', C['mauve'], 0, 1)

        # ── Fila alertas recientes ────────────────────────────────────────────
        bottom = ctk.CTkFrame(self, fg_color='transparent')
        bottom.pack(fill='x', padx=20, pady=(0, 16))
        bottom.columnconfigure((0,1), weight=1)

        alerts_card = ctk.CTkFrame(bottom, fg_color=C['surface0'],
                                   border_width=1, border_color=C['surface1'],
                                   corner_radius=12)
        alerts_card.grid(row=0, column=0, sticky='nsew', padx=(0,8), ipady=8)

        ctk.CTkLabel(alerts_card, text='ALERTAS RECIENTES',
                     font=ctk.CTkFont(size=9, weight='bold'),
                     text_color=C['overlay0']).pack(anchor='w', padx=16, pady=(12,6))

        self._alerts_frame = ctk.CTkScrollableFrame(
            alerts_card, fg_color='transparent', height=120)
        self._alerts_frame.pack(fill='both', expand=True, padx=8, pady=(0,8))

        stats_card = ctk.CTkFrame(bottom, fg_color=C['surface0'],
                                  border_width=1, border_color=C['surface1'],
                                  corner_radius=12)
        stats_card.grid(row=0, column=1, sticky='nsew', padx=(8,0), ipady=8)

        ctk.CTkLabel(stats_card, text='RESUMEN',
                     font=ctk.CTkFont(size=9, weight='bold'),
                     text_color=C['overlay0']).pack(anchor='w', padx=16, pady=(12,6))

        self._stats_frame = ctk.CTkFrame(stats_card, fg_color='transparent')
        self._stats_frame.pack(fill='both', padx=16, pady=(0,8))

    def _kpi(self, parent, label, value, color, col):
        card = ctk.CTkFrame(parent, fg_color=C['surface0'],
                            border_width=1, border_color=C['surface1'],
                            corner_radius=12)
        card.grid(row=0, column=col, sticky='nsew',
                  padx=(0 if col > 0 else 0, 6 if col < 4 else 0),
                  pady=0, ipady=10)

        ctk.CTkFrame(card, fg_color=color, height=3,
                     corner_radius=2).pack(fill='x', padx=14, pady=(12, 6))

        val_lbl = ctk.CTkLabel(card, text=value,
                               font=ctk.CTkFont(size=26, weight='bold'),
                               text_color=color)
        val_lbl.pack()
        ctk.CTkLabel(card, text=label,
                     font=ctk.CTkFont(size=10),
                     text_color=C['subtext']).pack(pady=(2, 10))
        return val_lbl

    def _make_chart(self, parent, title, color, row, col):
        card = ctk.CTkFrame(parent, fg_color=C['surface0'],
                            border_width=1, border_color=C['surface1'],
                            corner_radius=12)
        card.grid(row=row, column=col, sticky='nsew',
                  padx=(0 if col > 0 else 0, 6 if col == 0 else 0),
                  pady=0)

        ctk.CTkLabel(card, text=title,
                     font=ctk.CTkFont(size=11, weight='bold'),
                     text_color=C['subtext']).pack(anchor='w', padx=14, pady=(10,0))

        bg = _hex_to_rgb01(C['surface0'])
        fig, ax = plt.subplots(figsize=(4, 1.6), facecolor=bg)
        ax.set_facecolor(_hex_to_rgb01(C['base']))
        ax.tick_params(colors=_hex_to_rgb01(C['overlay0']), labelsize=7)
        for sp in ax.spines.values():
            sp.set_color(_hex_to_rgb01(C['surface1']))
        ax.set_ylim(0, 100)
        ax.set_xlim(0, 59)
        ax.set_yticks([0, 50, 100])
        ax.set_xticks([])

        rgb = _hex_to_rgb01(color)
        line, = ax.plot(range(60), [0]*60, color=rgb, linewidth=1.5)
        ax.fill_between(range(60), [0]*60, color=rgb, alpha=0.15)
        fig.tight_layout(pad=0.5)

        canvas = FigureCanvasTkAgg(fig, master=card)
        canvas.get_tk_widget().pack(fill='both', expand=True, padx=8, pady=(4,10))
        canvas.draw()

        self._figures.append((fig, ax, canvas, line))
        return fig, ax, canvas

    def _refresh(self):
        snap = self.monitor.snapshot()

        # KPIs
        self._kpi_cpu.configure(text=f'{snap["cpu"]:.0f}%')
        self._kpi_ram.configure(text=f'{snap["ram"]:.0f}%')
        self._kpi_disk.configure(text=f'{snap["disk"]:.0f}%')
        net_total = snap["net_sent"] + snap["net_recv"]
        self._kpi_net.configure(text=f'{net_total:.0f} KB/s')

        risk = snap['risk_score']
        risk_color = C['green'] if risk < 30 else C['yellow'] if risk < 60 else C['red']
        self._kpi_risk.configure(text=str(risk), text_color=risk_color)

        # Gráficas CPU y RAM
        cpu_data = snap['cpu_hist']
        ram_data = snap['ram_hist']

        fig_cpu, ax_cpu, canvas_cpu = self._figures[0][0], self._figures[0][1], self._figures[0][2]
        line_cpu = self._figures[0][3]
        line_cpu.set_ydata(cpu_data)
        # Fill
        for coll in ax_cpu.collections:
            coll.remove()
        ax_cpu.fill_between(range(60), cpu_data, color=_hex_to_rgb01(C['blue']), alpha=0.15)
        canvas_cpu.draw_idle()

        fig_ram, ax_ram, canvas_ram = self._figures[1][0], self._figures[1][1], self._figures[1][2]
        line_ram = self._figures[1][3]
        line_ram.set_ydata(ram_data)
        for coll in ax_ram.collections:
            coll.remove()
        ax_ram.fill_between(range(60), ram_data, color=_hex_to_rgb01(C['mauve']), alpha=0.15)
        canvas_ram.draw_idle()

        # Alertas recientes
        for w in self._alerts_frame.winfo_children():
            w.destroy()
        alerts = db.get_alerts(status='open', limit=8)
        if not alerts:
            ctk.CTkLabel(self._alerts_frame, text='Sin alertas abiertas',
                         font=ctk.CTkFont(size=11), text_color=C['overlay0']).pack()
        for a in alerts:
            color = SEVERITY_COLOR.get(a['severity'], C['subtext'])
            row_f = ctk.CTkFrame(self._alerts_frame, fg_color='transparent')
            row_f.pack(fill='x', pady=2)
            ctk.CTkFrame(row_f, fg_color=color, width=3,
                         corner_radius=2).pack(side='left', fill='y', padx=(0,6))
            ctk.CTkLabel(row_f, text=a['title'][:55],
                         font=ctk.CTkFont(size=11), text_color=C['text'],
                         anchor='w').pack(side='left', fill='x', expand=True)

        # Resumen estadísticas
        for w in self._stats_frame.winfo_children():
            w.destroy()
        stats = db.get_stats()
        items = [
            ('Eventos totales', stats['total_events'], C['blue']),
            ('Alertas abiertas', stats['open_alerts'], C['yellow']),
            ('Alertas criticas', stats['critical'], C['red']),
            ('Procesos activos', len(snap['processes']), C['teal']),
            ('Conexiones activas', len(snap['connections']), C['green']),
        ]
        for label, val, color in items:
            r = ctk.CTkFrame(self._stats_frame, fg_color='transparent')
            r.pack(fill='x', pady=3)
            ctk.CTkLabel(r, text=label, font=ctk.CTkFont(size=11),
                         text_color=C['subtext']).pack(side='left')
            ctk.CTkLabel(r, text=str(val), font=ctk.CTkFont(size=11, weight='bold'),
                         text_color=color).pack(side='right')

        self.after(2000, self._refresh)

    def cargar(self):
        pass
