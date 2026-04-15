import tkinter as tk
from tkinter import ttk, messagebox
import serial
import serial.tools.list_ports

class VerbindungUI(ttk.Frame):
    def __init__(self, parent, serial_manager):
        super().__init__(parent)
        self.serial_manager = serial_manager


        # TOP FRAME: Connection settings
        conn_frame = ttk.LabelFrame(self, text="Verbindungseinstellungen", padding=10)
        conn_frame.pack(fill="x", pady=5)

        ttk.Label(conn_frame, text="COM Port:").grid(row=0, column=0, sticky="e", padx=5, pady=5)
        self.cb_port = ttk.Combobox(conn_frame, values=[p.device for p in serial.tools.list_ports.comports()], width=20)
        self.cb_port.grid(row=0, column=1, sticky="w", padx=5, pady=5)
        if self.cb_port['values']:
            self.cb_port.current(0)

        ttk.Label(conn_frame, text="Baud-Rate:").grid(row=1, column=0, sticky="e", padx=5, pady=5)
        self.cb_baud = ttk.Combobox(conn_frame, values=["2400", "9600"], width=20)
        self.cb_baud.set("9600")
        self.cb_baud.grid(row=1, column=1, sticky="w", padx=5, pady=5)

        btn_frame = ttk.Frame(conn_frame)
        btn_frame.grid(row=2, column=0, columnspan=2, pady=10)

        self.btn_connect = ttk.Button(btn_frame, text="Verbinden", command=self.toggle_connection)
        self.btn_connect.pack(side="left", padx=5)

        ttk.Button(btn_frame, text="Force Init (W @ 2400)", command=self.force_init).pack(side="left", padx=5)

        # BOTTOM FRAME: Log
        log_frame = ttk.LabelFrame(self, text="Kommunikation mit DISAG RM III", padding=5)
        log_frame.pack(fill="both", expand=True, pady=5)

        self.txt_log = tk.Text(log_frame, state="disabled", bg="#1e1e1e", fg="#d4d4d4", font=("Consolas", 10))
        self.txt_log.pack(fill="both", expand=True)
        self.txt_log.tag_config("in", foreground="#b5cea8")
        self.txt_log.tag_config("out", foreground="#569cd6")
        self.txt_log.tag_config("sys", foreground="#ce9178")
        self.txt_log.tag_config("err", foreground="#f44747")

        # Register this log widget with the SerialManager
        self.serial_manager.add_log_widget(self.txt_log)

    def toggle_connection(self):
        if self.serial_manager.is_connected():
            self.serial_manager.disconnect()
            self.btn_connect.config(text="Verbinden")
        else:
            port = self.cb_port.get()
            baud = self.cb_baud.get()
            if not port:
                messagebox.showerror("Fehler", "Bitte einen COM Port auswählen.")
                return

            try:
                self.serial_manager.connect(port, int(baud))
                self.btn_connect.config(text="Trennen")
            except Exception as e:
                messagebox.showerror("Fehler", f"Verbindung fehlgeschlagen:\n{str(e)}")

    def force_init(self):
        port = self.cb_port.get()
        if not port:
            messagebox.showerror("Fehler", "Bitte einen COM Port auswählen.")
            return

        was_connected = self.serial_manager.is_connected()
        if was_connected:
            self.serial_manager.disconnect()
            self.btn_connect.config(text="Verbinden")

        try:
            self.serial_manager.log(">> Sende W+CR mit 2400 Bd...", "out")
            with serial.Serial(port, 2400, timeout=1) as s:
                s.write(b"W\r")
                self.serial_manager.log(">> W+CR gesendet.", "sys")
        except Exception as e:
            self.serial_manager.log(f"Force Init fehlgeschlagen: {e}", "err")

        # Reconnect if we were connected before
        if was_connected:
            self.toggle_connection()
