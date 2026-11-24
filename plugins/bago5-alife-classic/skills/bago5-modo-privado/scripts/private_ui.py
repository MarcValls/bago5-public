"""Local handoff UI; no secret fields, observer APIs or model RPC endpoints."""
from __future__ import annotations
import threading
import tkinter as tk
from tkinter import ttk
from private_mode import Coordinator, Denied, State


class PrivateDialog:
    def __init__(self, root: tk.Tk, coordinator: Coordinator):
        self.root, self.coordinator = root, coordinator
        self.busy = False
        self._alive = True
        self._result: tuple[object, str | None] | None = None
        root.title('BAGO5 · Cesión privada')
        root.geometry('660x440')
        root.minsize(600, 420)
        root.protocol('WM_DELETE_WINDOW', self.close)
        frame = ttk.Frame(root, padding=24)
        frame.pack(fill='both', expand=True)
        ttk.Label(frame, text='KeePassXC · Control del usuario', font=('Segoe UI', 16, 'bold')).pack(anchor='w')
        self.state = tk.StringVar(value=coordinator.gate.snapshot().state.value)
        ttk.Label(frame, textvariable=self.state, font=('Segoe UI', 13, 'bold')).pack(anchor='w', pady=(14, 8))
        ttk.Label(frame, wraplength=600, justify='left', text=(
            'Introduce servicio, cuenta y contraseña únicamente en KeePassXC, nunca aquí ni en el chat. '
            'La barrera cubre solo las herramientas del host que estén realmente integradas. '
            'No protege frente a otros programas del dispositivo.')).pack(anchor='w')
        self.note = tk.StringVar(value='No se ha abierto el gestor. Sin una barrera del host verificable, la operación se bloquea.')
        ttk.Label(frame, textvariable=self.note, wraplength=600, justify='left').pack(anchor='w', pady=14)
        self.confirmed = tk.BooleanVar(value=False)
        self.confirm = ttk.Checkbutton(frame, variable=self.confirmed, command=self.refresh,
            text='He bloqueado o cerrado KeePassXC y tratado el portapapeles, si lo utilicé.')
        self.confirm.pack(anchor='w', pady=(0, 14))
        row = ttk.Frame(frame)
        row.pack(fill='x')
        self.open_button = ttk.Button(row, text='Abrir KeePassXC', command=self.open_private)
        self.open_button.pack(side='left')
        self.done_button = ttk.Button(row, text='He terminado', command=lambda: self.resume('done'))
        self.done_button.pack(side='left', padx=8)
        self.cancel_button = ttk.Button(frame, text='Cancelar · mantener bloqueo', command=self.cancel)
        self.cancel_button.pack(anchor='w', pady=(12, 0))
        self.resume_button = ttk.Button(frame, text='Reanudar sin confirmar guardado', command=lambda: self.resume('cancel'))
        self.resume_button.pack(anchor='w', pady=(8, 0))
        self.refresh()

    def refresh(self) -> None:
        try:
            state = self.coordinator.gate.snapshot().state
        except Denied:
            state = State.BLOCKED
            self.note.set('Almacén de control no disponible. No reanudar observación.')
        self.state.set(state.value)
        self.open_button.configure(state='normal' if state == State.NORMAL and not self.busy else 'disabled')
        self.done_button.configure(state='normal' if state == State.PRIVATE and self.confirmed.get() and not self.busy else 'disabled')
        self.resume_button.configure(state='normal' if state in {State.CANCELLED, State.BLOCKED} and self.confirmed.get() and not self.busy else 'disabled')
        self.cancel_button.configure(state='normal' if state in {State.PRIVATE, State.BLOCKED, State.CANCELLED} and not self.busy else 'disabled')

    def open_private(self) -> None:
        if self.busy:
            return
        self.busy = True
        self.confirmed.set(False)
        self.note.set('Preparando la cesión. No introduzcas todavía ningún secreto.')
        self.refresh()
        def work() -> None:
            try:
                self._result = (self.coordinator.start(), None)
            except Denied as error:
                self._result = (None, error.code.value)
            except Exception:
                self._result = (None, 'HOST_FAILURE')
        threading.Thread(target=work, daemon=True).start()
        self.root.after(25, self._poll)

    def _poll(self) -> None:
        if not self._alive:
            return
        if self._result is None:
            self.root.after(25, self._poll)
            return
        _, error = self._result
        self._result = None
        self.busy = False
        self.note.set(('Bloqueado: ' + error + '. No introduzcas secretos.') if error else
                      'Interacción privada abierta. BAGO no verificará el contenido ni el guardado.')
        self.refresh()

    def cancel(self) -> None:
        try:
            self.coordinator.cancel()
            self.note.set('Operación sin confirmar. La observación sigue bloqueada hasta una reanudación explícita.')
        except Denied:
            self.note.set('La sesión no puede reanudarse desde aquí. Requiere reconciliación del host.')
        self.confirmed.set(False)
        self.refresh()

    def resume(self, action: str) -> None:
        if self.busy:
            return
        try:
            result = self.coordinator.finish(action, safe_to_resume=self.confirmed.get())
            self.note.set('Interacción finalizada por el usuario; guardado NO VERIFICADO.' if result['user_finished'] else
                          'Operación cancelada; resultado sin confirmar. Se admiten únicamente nuevas solicitudes.')
        except Denied as error:
            self.note.set('No reanudado: ' + error.code.value)
        self.confirmed.set(False)
        self.refresh()

    def close(self) -> None:
        if self.busy:
            self.coordinator.request_cancel()
            # Do not close while a launch handshake is in flight. Cancellation
            # takes effect after the bounded host operation returns; never reopen.
            self.note.set('Preparación en curso. No introduzcas secretos. El cierre no reanudará herramientas.')
            self.root.after(50, self.close)
            return
        try:
            if self.coordinator.gate.snapshot().state != State.NORMAL:
                self.coordinator.cancel()
        except Denied:
            pass
        self._alive = False
        self.root.destroy()


def show(coordinator: Coordinator) -> None:
    root = tk.Tk()
    PrivateDialog(root, coordinator)
    root.mainloop()
