import customtkinter as ctk
import requests, threading
from theme import C

SERVER = 'https://alisson-voz-server-production.up.railway.app'


def verificar_licencia(clave: str) -> dict:
    try:
        r = requests.get(f'{SERVER}/api/validar',
                         params={'clave': clave, 'prog': 'Sentinel'},
                         timeout=8)
        return r.json()
    except Exception:
        return {'valida': False, 'mensaje': 'Sin conexión al servidor'}


class VentanaLicencia(ctk.CTkToplevel):
    def __init__(self, master, on_success):
        super().__init__(master)
        self.on_success = on_success
        self.title('DeepCore Sentinel — Activación')
        self.geometry('440x320')
        self.resizable(False, False)
        self.configure(fg_color=C['base'])
        self.grab_set()
        self._center()
        self._build()

    def _center(self):
        self.update_idletasks()
        x = (self.winfo_screenwidth()  - 440) // 2
        y = (self.winfo_screenheight() - 320) // 2
        self.geometry(f'+{x}+{y}')

    def _build(self):
        ctk.CTkFrame(self, fg_color=C['sentinel'], height=3).pack(fill='x')

        top = ctk.CTkFrame(self, fg_color=C['mantle'], height=64)
        top.pack(fill='x')
        top.pack_propagate(False)
        badge = ctk.CTkFrame(top, fg_color=C['sentinel'], width=44, height=34,
                             corner_radius=8)
        badge.place(x=18, rely=0.5, anchor='w')
        badge.pack_propagate(False)
        ctk.CTkLabel(badge, text='DC', font=ctk.CTkFont(size=14, weight='bold'),
                     text_color='#fff').place(relx=0.5, rely=0.5, anchor='center')
        ctk.CTkLabel(top, text='DeepCore Sentinel',
                     font=ctk.CTkFont(size=16, weight='bold'),
                     text_color=C['text']).place(x=74, rely=0.5, anchor='w')

        body = ctk.CTkFrame(self, fg_color=C['base'])
        body.pack(fill='both', expand=True, padx=32, pady=24)

        ctk.CTkLabel(body, text='Ingresa tu clave de licencia',
                     font=ctk.CTkFont(size=13), text_color=C['subtext']).pack(pady=(0, 14))

        self._entry = ctk.CTkEntry(body, placeholder_text='XXXX-XXXX-XXXX-XXXX',
                                   height=42, corner_radius=8,
                                   fg_color=C['surface0'], border_color=C['surface2'],
                                   text_color=C['text'],
                                   placeholder_text_color=C['overlay0'],
                                   font=ctk.CTkFont(size=15, family='Courier New'))
        self._entry.pack(fill='x', pady=(0, 8))
        self._entry.bind('<Return>', lambda _: self._activate())

        self._btn = ctk.CTkButton(body, text='Activar', height=42, corner_radius=8,
                                  fg_color=C['green'], hover_color=C['teal'],
                                  text_color='#000', font=ctk.CTkFont(size=13, weight='bold'),
                                  command=self._activate)
        self._btn.pack(fill='x', pady=(0, 10))

        self._msg = ctk.CTkLabel(body, text='', font=ctk.CTkFont(size=12),
                                 text_color=C['red'])
        self._msg.pack()

        ctk.CTkLabel(body,
                     text='Obtén tu licencia en deepcore.ec · Soporte: +593 986 225 038',
                     font=ctk.CTkFont(size=10), text_color=C['overlay0']).pack(side='bottom')

    def _activate(self):
        clave = self._entry.get().strip()
        if not clave:
            self._msg.configure(text='Ingresa la clave.')
            return
        self._btn.configure(state='disabled', text='Verificando...')
        self._msg.configure(text='')
        threading.Thread(target=self._check, args=(clave,), daemon=True).start()

    def _check(self, clave: str):
        result = verificar_licencia(clave)
        self.after(0, self._handle, result)

    def _handle(self, result: dict):
        self._btn.configure(state='normal', text='Activar')
        if result.get('valida'):
            self._msg.configure(text=result.get('mensaje', ''), text_color=C['green'])
            self.after(800, lambda: (self.destroy(), self.on_success()))
        else:
            self._msg.configure(text=result.get('mensaje', 'Clave inválida'),
                                text_color=C['red'])
