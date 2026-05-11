import customtkinter as ctk
from tkinter import ttk, filedialog
import threading, hashlib, os
from datetime import datetime
from theme import C
import database as db

try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler
    WATCHDOG_OK = True
except ImportError:
    WATCHDOG_OK = False


class _Handler(FileSystemEventHandler):
    def __init__(self, callback):
        self._cb = callback

    def on_created(self, event):
        if not event.is_directory:
            self._cb('creado', event.src_path)

    def on_modified(self, event):
        if not event.is_directory:
            self._cb('modificado', event.src_path)

    def on_deleted(self, event):
        if not event.is_directory:
            self._cb('eliminado', event.src_path)

    def on_moved(self, event):
        self._cb('movido', event.dest_path)


class ArchivosPanel(ctk.CTkFrame):
    def __init__(self, master, **kw):
        super().__init__(master, fg_color=C['base'], **kw)
        self._observers: dict = {}      # path → Observer
        self._build()
        self._load_paths()
        self._refresh_events()

    def _build(self):
        top = ctk.CTkFrame(self, fg_color=C['mantle'],
                           border_width=1, border_color=C['surface1'],
                           corner_radius=0)
        top.pack(fill='x')

        ctk.CTkLabel(top, text='Integridad de Archivos',
                     font=ctk.CTkFont(size=18, weight='bold'),
                     text_color=C['text']).pack(side='left', padx=20, pady=14)

        if not WATCHDOG_OK:
            ctk.CTkLabel(top, text='watchdog no instalado — modo lectura',
                         font=ctk.CTkFont(size=11),
                         text_color=C['yellow']).pack(side='right', padx=20)

        body = ctk.CTkFrame(self, fg_color='transparent')
        body.pack(fill='both', expand=True, padx=20, pady=16)
        body.columnconfigure(0, weight=1)
        body.columnconfigure(1, weight=2)
        body.rowconfigure(0, weight=1)

        # ── Panel izquierdo: rutas vigiladas ─────────────────────────────────
        left = ctk.CTkFrame(body, fg_color=C['surface0'],
                            border_width=1, border_color=C['surface1'],
                            corner_radius=12)
        left.grid(row=0, column=0, sticky='nsew', padx=(0,10))

        ctk.CTkLabel(left, text='RUTAS VIGILADAS',
                     font=ctk.CTkFont(size=9, weight='bold'),
                     text_color=C['overlay0']).pack(anchor='w', padx=16, pady=(14,6))

        self._paths_frame = ctk.CTkScrollableFrame(left, fg_color='transparent')
        self._paths_frame.pack(fill='both', expand=True, padx=8, pady=(0,8))

        btn_row = ctk.CTkFrame(left, fg_color='transparent')
        btn_row.pack(fill='x', padx=12, pady=(0,12))

        ctk.CTkButton(btn_row, text='Agregar carpeta',
                      height=34, corner_radius=8,
                      fg_color=C['green'], hover_color=C['teal'],
                      text_color='#000', font=ctk.CTkFont(size=12, weight='bold'),
                      command=self._add_path).pack(fill='x')

        # ── Panel derecho: eventos de archivos ────────────────────────────────
        right = ctk.CTkFrame(body, fg_color=C['surface0'],
                             border_width=1, border_color=C['surface1'],
                             corner_radius=12)
        right.grid(row=0, column=1, sticky='nsew')

        ctk.CTkLabel(right, text='EVENTOS RECIENTES',
                     font=ctk.CTkFont(size=9, weight='bold'),
                     text_color=C['overlay0']).pack(anchor='w', padx=16, pady=(14,6))

        style = ttk.Style()
        style.configure('File.Treeview',
            background=C['surface0'], foreground=C['text'],
            fieldbackground=C['surface0'], rowheight=24,
            borderwidth=0, font=('Segoe UI', 10))
        style.configure('File.Treeview.Heading',
            background=C['mantle'], foreground=C['blue'],
            font=('Segoe UI', 10, 'bold'), relief='flat')
        style.map('File.Treeview',
            background=[('selected', C['surface1'])],
            foreground=[('selected', C['text'])])

        cols = ('ts', 'tipo', 'archivo')
        self._tree = ttk.Treeview(right, columns=cols,
                                   show='headings', style='File.Treeview')
        self._tree.heading('ts',      text='Hora')
        self._tree.heading('tipo',    text='Evento')
        self._tree.heading('archivo', text='Archivo')
        self._tree.column('ts',      width=80,  anchor='center')
        self._tree.column('tipo',    width=90,  anchor='center')
        self._tree.column('archivo', width=400, anchor='w')

        self._tree.tag_configure('creado',     foreground=C['green'])
        self._tree.tag_configure('modificado', foreground=C['yellow'])
        self._tree.tag_configure('eliminado',  foreground=C['red'])
        self._tree.tag_configure('movido',     foreground=C['blue'])

        sb = ttk.Scrollbar(right, orient='vertical',
                           command=self._tree.yview)
        self._tree.configure(yscrollcommand=sb.set)
        self._tree.pack(side='left', fill='both', expand=True, padx=2, pady=2)
        sb.pack(side='right', fill='y', pady=2)

    def _load_paths(self):
        for w in self._paths_frame.winfo_children():
            w.destroy()
        paths = db.get_watched_paths()
        if not paths:
            ctk.CTkLabel(self._paths_frame,
                         text='Sin rutas configuradas.\nAgrega una carpeta para empezar.',
                         font=ctk.CTkFont(size=11),
                         text_color=C['overlay0'], justify='center').pack(pady=20)
            return
        for p in paths:
            self._path_row(p)
            # Iniciar observer si watchdog disponible
            if WATCHDOG_OK and p['path'] not in self._observers:
                self._start_observer(p['path'])

    def _path_row(self, p: dict):
        row = ctk.CTkFrame(self._paths_frame, fg_color=C['surface1'],
                           corner_radius=8)
        row.pack(fill='x', pady=3)

        ctk.CTkFrame(row, fg_color=C['teal'], width=3,
                     corner_radius=2).pack(side='left', fill='y')

        ctk.CTkLabel(row, text=p['path'][:45],
                     font=ctk.CTkFont(size=11), text_color=C['text'],
                     anchor='w').pack(side='left', padx=10, pady=8, fill='x', expand=True)

        ctk.CTkButton(row, text='X', width=28, height=28,
                      corner_radius=6, fg_color='transparent',
                      text_color=C['red'], hover_color=C['red'],
                      command=lambda pid=p['id'], path=p['path']: self._remove(pid, path)
                      ).pack(side='right', padx=6)

    def _add_path(self):
        path = filedialog.askdirectory(title='Selecciona carpeta a vigilar')
        if path:
            db.add_watched_path(path)
            self._load_paths()

    def _remove(self, path_id: int, path: str):
        db.remove_watched_path(path_id)
        obs = self._observers.pop(path, None)
        if obs:
            obs.stop()
        self._load_paths()

    def _start_observer(self, path: str):
        try:
            handler  = _Handler(lambda etype, fpath: self._on_file_event(etype, fpath))
            observer = Observer()
            observer.schedule(handler, path, recursive=True)
            observer.start()
            self._observers[path] = observer
        except Exception:
            pass

    def _on_file_event(self, etype: str, fpath: str):
        sha = None
        if etype in ('creado', 'modificado'):
            try:
                with open(fpath, 'rb') as f:
                    sha = hashlib.sha256(f.read(512 * 1024)).hexdigest()
            except Exception:
                pass
        db.insert_file_event(etype, fpath, sha)
        # Alerta si archivo en ruta crítica
        if any(k in fpath.lower() for k in ('\\system32\\', '\\windows\\',
                                              '/etc/', '/bin/', '/sbin/')):
            db.insert_alert(3, f'Cambio en archivo del sistema',
                            f'{etype}: {fpath}', 'archivos')
        self.after(0, self._refresh_events)

    def _refresh_events(self):
        events = db.get_file_events(limit=200)
        self._tree.delete(*self._tree.get_children())
        for e in events:
            hora = e['ts'][11:19]
            self._tree.insert('', 'end',
                              values=(hora, e['etype'], e['path']),
                              tags=(e['etype'],))
        self.after(10000, self._refresh_events)

    def cargar(self):
        self._load_paths()
        self._refresh_events()
