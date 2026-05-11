import customtkinter as ctk
from tkinter import filedialog
from datetime import datetime
from theme import C, SEVERITY_LABEL
import database as db

try:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import cm
    PDF_OK = True
except ImportError:
    PDF_OK = False


class ReportesPanel(ctk.CTkFrame):
    def __init__(self, master, monitor, **kw):
        super().__init__(master, fg_color=C['base'], **kw)
        self.monitor = monitor
        self._build()

    def _build(self):
        top = ctk.CTkFrame(self, fg_color=C['mantle'],
                           border_width=1, border_color=C['surface1'],
                           corner_radius=0)
        top.pack(fill='x')
        ctk.CTkLabel(top, text='Reportes de Seguridad',
                     font=ctk.CTkFont(size=18, weight='bold'),
                     text_color=C['text']).pack(side='left', padx=20, pady=14)

        body = ctk.CTkFrame(self, fg_color='transparent')
        body.pack(fill='both', expand=True, padx=40, pady=30)
        body.columnconfigure((0,1), weight=1)

        # ── Tarjeta resumen del sistema ────────────────────────────────────────
        self._summary_card(body)

        # ── Opciones de exportación ────────────────────────────────────────────
        exp_card = ctk.CTkFrame(body, fg_color=C['surface0'],
                                border_width=1, border_color=C['surface1'],
                                corner_radius=14)
        exp_card.grid(row=1, column=0, columnspan=2, sticky='ew',
                      pady=(20, 0))

        ctk.CTkLabel(exp_card, text='EXPORTAR REPORTE',
                     font=ctk.CTkFont(size=9, weight='bold'),
                     text_color=C['overlay0']).pack(anchor='w', padx=20, pady=(16,10))

        btns = ctk.CTkFrame(exp_card, fg_color='transparent')
        btns.pack(padx=20, pady=(0,20))

        ctk.CTkButton(btns, text='Exportar PDF',
                      width=180, height=44, corner_radius=10,
                      fg_color=C['sentinel'], hover_color='#c0001f',
                      text_color='#fff', font=ctk.CTkFont(size=13, weight='bold'),
                      state='normal' if PDF_OK else 'disabled',
                      command=self._export_pdf).pack(side='left', padx=(0,12))

        ctk.CTkButton(btns, text='Exportar TXT',
                      width=180, height=44, corner_radius=10,
                      fg_color=C['surface1'], hover_color=C['surface2'],
                      text_color=C['text'], font=ctk.CTkFont(size=13),
                      command=self._export_txt).pack(side='left')

        if not PDF_OK:
            ctk.CTkLabel(exp_card,
                         text='Para PDF: pip install reportlab',
                         font=ctk.CTkFont(size=10),
                         text_color=C['yellow']).pack(pady=(0,12))

        self._status_lbl = ctk.CTkLabel(exp_card, text='',
                                         font=ctk.CTkFont(size=12),
                                         text_color=C['green'])
        self._status_lbl.pack(pady=(0,12))

    def _summary_card(self, parent):
        card = ctk.CTkFrame(parent, fg_color=C['surface0'],
                            border_width=1, border_color=C['surface1'],
                            corner_radius=14)
        card.grid(row=0, column=0, columnspan=2, sticky='ew')

        ctk.CTkLabel(card, text='RESUMEN DEL SISTEMA',
                     font=ctk.CTkFont(size=9, weight='bold'),
                     text_color=C['overlay0']).pack(anchor='w', padx=20, pady=(16,10))

        stats = db.get_stats()
        snap  = self.monitor.snapshot()
        counts = db.count_alerts_by_severity()

        grid = ctk.CTkFrame(card, fg_color='transparent')
        grid.pack(fill='x', padx=20, pady=(0,16))
        grid.columnconfigure((0,1,2,3), weight=1)

        items = [
            ('Total eventos',     stats['total_events'],  C['blue'],   0),
            ('Alertas abiertas',  stats['open_alerts'],   C['yellow'], 1),
            ('Alertas criticas',  counts.get(4, 0),       C['red'],    2),
            ('Score de riesgo',   f'{snap["risk_score"]}/100', C['orange'], 3),
        ]
        for label, val, color, col in items:
            f = ctk.CTkFrame(grid, fg_color=C['surface1'], corner_radius=10)
            f.grid(row=0, column=col, sticky='nsew',
                   padx=(0 if col == 0 else 6, 6 if col < 3 else 0), ipady=10)
            ctk.CTkLabel(f, text=str(val),
                         font=ctk.CTkFont(size=24, weight='bold'),
                         text_color=color).pack(pady=(10,2))
            ctk.CTkLabel(f, text=label, font=ctk.CTkFont(size=10),
                         text_color=C['subtext']).pack(pady=(0,10))

    def _build_report_data(self) -> dict:
        stats  = db.get_stats()
        alerts = db.get_alerts(limit=100)
        events = db.get_events(limit=50)
        snap   = self.monitor.snapshot()
        counts = db.count_alerts_by_severity()
        return {
            'generated': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'stats':  stats,
            'alerts': alerts,
            'events': events,
            'snap':   snap,
            'counts': counts,
        }

    def _export_txt(self):
        path = filedialog.asksaveasfilename(
            defaultextension='.txt',
            filetypes=[('Texto', '*.txt')],
            initialfile=f'sentinel_{datetime.now().strftime("%Y%m%d_%H%M")}.txt')
        if not path:
            return
        data = self._build_report_data()
        lines = [
            '=' * 60,
            'DEEPCORE SENTINEL — REPORTE DE SEGURIDAD',
            f'Generado: {data["generated"]}',
            '=' * 60,
            '',
            '--- RESUMEN GENERAL ---',
            f'Total eventos registrados : {data["stats"]["total_events"]}',
            f'Alertas abiertas          : {data["stats"]["open_alerts"]}',
            f'Alertas criticas          : {data["counts"].get(4, 0)}',
            f'Alertas altas             : {data["counts"].get(3, 0)}',
            f'Score de riesgo actual    : {data["snap"]["risk_score"]}/100',
            '',
            '--- ULTIMAS 50 ALERTAS ABIERTAS ---',
        ]
        open_alerts = [a for a in data['alerts'] if a['status'] == 'open'][:50]
        for a in open_alerts:
            sev = SEVERITY_LABEL.get(a['severity'], 'Info')
            lines.append(f"[{sev}] {a['ts'][:19]} | {a['category']} | {a['title']}")

        lines += ['', '--- ULTIMOS 50 EVENTOS ---']
        for e in data['events']:
            lines.append(f"{e['ts'][:19]} | {e['category']} | {e['title']}")

        with open(path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))
        self._status_lbl.configure(text=f'Exportado: {path}')

    def _export_pdf(self):
        if not PDF_OK:
            return
        path = filedialog.asksaveasfilename(
            defaultextension='.pdf',
            filetypes=[('PDF', '*.pdf')],
            initialfile=f'sentinel_{datetime.now().strftime("%Y%m%d_%H%M")}.pdf')
        if not path:
            return

        data   = self._build_report_data()
        doc    = SimpleDocTemplate(path, pagesize=A4,
                                   leftMargin=2*cm, rightMargin=2*cm,
                                   topMargin=2*cm, bottomMargin=2*cm)
        styles = getSampleStyleSheet()
        story  = []

        title_style = ParagraphStyle('Title2', parent=styles['Title'],
                                      fontSize=18, textColor=colors.HexColor('#E8002A'))
        h2_style    = ParagraphStyle('H2', parent=styles['Heading2'],
                                      fontSize=12, textColor=colors.HexColor('#60A5FA'))

        story.append(Paragraph('DeepCore Sentinel — Reporte de Seguridad', title_style))
        story.append(Paragraph(f'Generado: {data["generated"]}', styles['Normal']))
        story.append(Spacer(1, 0.5*cm))

        story.append(Paragraph('Resumen General', h2_style))
        summary_data = [
            ['Métrica', 'Valor'],
            ['Total eventos', str(data['stats']['total_events'])],
            ['Alertas abiertas', str(data['stats']['open_alerts'])],
            ['Alertas críticas', str(data['counts'].get(4, 0))],
            ['Alertas altas', str(data['counts'].get(3, 0))],
            ['Score de riesgo', f'{data["snap"]["risk_score"]}/100'],
        ]
        t = Table(summary_data, colWidths=[10*cm, 6*cm])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#1E293B')),
            ('TEXTCOLOR',  (0,0), (-1,0), colors.HexColor('#60A5FA')),
            ('FONTSIZE',   (0,0), (-1,-1), 10),
            ('ROWBACKGROUNDS', (0,1), (-1,-1),
             [colors.HexColor('#0F172A'), colors.HexColor('#1E293B')]),
            ('TEXTCOLOR',  (0,1), (-1,-1), colors.white),
            ('GRID',       (0,0), (-1,-1), 0.5, colors.HexColor('#334155')),
            ('PADDING',    (0,0), (-1,-1), 6),
        ]))
        story.append(t)
        story.append(Spacer(1, 0.5*cm))

        story.append(Paragraph('Últimas 50 Alertas Abiertas', h2_style))
        open_alerts = [a for a in data['alerts'] if a['status'] == 'open'][:50]
        alert_data = [['#', 'Fecha', 'Severidad', 'Categoría', 'Alerta']]
        for a in open_alerts:
            alert_data.append([
                str(a['id']), a['ts'][:19],
                SEVERITY_LABEL.get(a['severity'], ''),
                a['category'], a['title'][:60]
            ])
        if len(alert_data) > 1:
            at = Table(alert_data, colWidths=[1*cm, 3.5*cm, 2*cm, 2.5*cm, 8*cm])
            at.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#1E293B')),
                ('TEXTCOLOR',  (0,0), (-1,0), colors.HexColor('#60A5FA')),
                ('FONTSIZE',   (0,0), (-1,-1), 8),
                ('ROWBACKGROUNDS', (0,1), (-1,-1),
                 [colors.HexColor('#0F172A'), colors.HexColor('#1E293B')]),
                ('TEXTCOLOR',  (0,1), (-1,-1), colors.white),
                ('GRID',       (0,0), (-1,-1), 0.5, colors.HexColor('#334155')),
                ('PADDING',    (0,0), (-1,-1), 4),
            ]))
            story.append(at)

        doc.build(story)
        self._status_lbl.configure(text=f'PDF generado: {path}')

    def cargar(self):
        pass
