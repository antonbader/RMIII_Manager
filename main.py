import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog
import serial
import serial.tools.list_ports
import threading
import time
import csv

# Protokoll-Konstanten laut Handbuch [cite: 8-13]
STX, ENQ, ACK, NAK, CR = b'\x02', b'\x05', b'\x06', b'\x15', b'\x0D'

class DisagRM3Ultimate(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("DISAG RM III - Ultimate Control & Logger")
        self.geometry("1100x900")
        
        self.ser = None
        self.running = False
        self._stx_received = False
        self._last_status = ""
        self.shot_results = []

        self.setup_ui()

    def calc_cs(self, data):
        """XOR-Checksumme laut Spezifikation: Falls < 32, addiere 32[cite: 63]."""
        cs = 0
        for char in data:
            cs ^= ord(char)
        if cs < 32:
            cs += 32
        return chr(cs)

    def setup_ui(self):
        # --- RECHTS: MONITOR ---
        log_frame = ttk.LabelFrame(self, text="Kommunikation & Datenstrom", padding=5)
        log_frame.pack(side="right", fill="both", expand=True, padx=5, pady=5)
        self.txt_log = scrolledtext.ScrolledText(log_frame, bg="#1e1e1e", fg="#d4d4d4", font=("Consolas", 10))
        self.txt_log.pack(fill="both", expand=True)
        self.txt_log.tag_config("in", foreground="#b5cea8")
        self.txt_log.tag_config("out", foreground="#569cd6")
        self.txt_log.tag_config("sys", foreground="#ce9178")

        # --- LINKS: BEDIENUNG ---
        left_panel = ttk.Frame(self)
        left_panel.pack(side="left", fill="y", padx=5, pady=5)

        # 1. Verbindung
        conn = ttk.LabelFrame(left_panel, text="1. Verbindung", padding=5)
        conn.pack(fill="x", pady=5)
        self.port_cb = ttk.Combobox(conn, values=[p.device for p in serial.tools.list_ports.comports()], width=15)
        self.port_cb.pack(pady=2)
        if self.port_cb['values']: self.port_cb.current(0)
        self.baud_cb = ttk.Combobox(conn, values=["2400", "9600", "19200", "38400"], width=15)
        self.baud_cb.set("9600")
        self.baud_cb.pack(pady=2)
        self.btn_conn = ttk.Button(conn, text="Verbinden", command=self.toggle_conn)
        self.btn_conn.pack(fill="x", pady=2)
        ttk.Button(conn, text="Force INIT (W @ 2400)", command=self.force_init).pack(fill="x")

        # 2. Einstellungen [cite: 65-111, 123-135]
        sett = ttk.LabelFrame(left_panel, text="2. Konfiguration", padding=5)
        sett.pack(fill="x", pady=5)
        
        ttk.Label(sett, text="Scheibe (SCH):").grid(row=0, column=0, sticky="w")
        self.sch_cb = ttk.Combobox(sett, values=["LG10", "LG5", "LGES", "LP", "ZS", "LS1", "LS2", "KK50", "GK10", "GK5", "LPSF", "SCHFE"], width=10)
        self.sch_cb.set("LG10")
        self.sch_cb.grid(row=0, column=1, pady=2, sticky="ew")

        ttk.Label(sett, text="Ringe (RIA):").grid(row=1, column=0, sticky="w")
        self.ria_cb = ttk.Combobox(sett, values=["GR", "ZR", "KR"], width=10)
        self.ria_cb.set("ZR")
        self.ria_cb.grid(row=1, column=1, pady=2, sticky="ew")

        ttk.Label(sett, text="Kaliber (KAL):").grid(row=2, column=0, sticky="w")
        self.kal_cb = ttk.Combobox(sett, values=["22", "4.5", "6MM", "7MM", "32", "38", "9MM", "45"], width=10)
        self.kal_cb.set("4.5")
        self.kal_cb.grid(row=2, column=1, pady=2, sticky="ew")

        ttk.Label(sett, text="Schuss/Sch. (SSC):").grid(row=3, column=0, sticky="w")
        self.ssc_val = ttk.Spinbox(sett, from_=1, to=15, width=9)
        self.ssc_val.set(1)
        self.ssc_val.grid(row=3, column=1, pady=2, sticky="ew")

        ttk.Button(sett, text="Setup senden", command=self.send_full_settings).grid(row=4, column=0, columnspan=2, pady=5, sticky="ew")

        # 3. Ergebnisse & Export [cite: 196-203]
        res_frame = ttk.LabelFrame(left_panel, text="3. Ergebnisse", padding=5)
        res_frame.pack(fill="x", pady=5)
        self.lbl_count = ttk.Label(res_frame, text="Erfasste Schüsse: 0")
        self.lbl_count.pack(pady=2)
        ttk.Button(res_frame, text="Als CSV speichern", command=self.save_csv).pack(fill="x", pady=2)

        # 4. Befehle [cite: 146-162]
        cmds = ttk.LabelFrame(left_panel, text="4. Befehle", padding=5)
        cmds.pack(fill="x", pady=5)
        ttk.Button(cmds, text="SNR? (Seriennummer)", command=lambda: self.send_prot("SNR")).pack(fill="x", pady=2)
        ttk.Button(cmds, text="Abbruch (ABR)", command=lambda: self.send_prot("ABR")).pack(fill="x", pady=2)

    def log(self, msg, tag="sys"):
        if "WSC=" in msg:
            if msg == self._last_status: return
            self._last_status = msg
        ts = time.strftime("%H:%M:%S")
        self.txt_log.configure(state='normal')
        self.txt_log.insert("end", f"[{ts}] {msg}\n", tag)
        self.txt_log.see("end")
        self.txt_log.configure(state='disabled')

    def toggle_conn(self):
        if self.ser and self.ser.is_open:
            self.running = False
            self.ser.close()
            self.btn_conn.config(text="Verbinden")
        else:
            try:
                self.ser = serial.Serial(self.port_cb.get(), int(self.baud_cb.get()), timeout=0.1)
                self.running = True
                threading.Thread(target=self.reader, daemon=True).start()
                self.btn_conn.config(text="Trennen")
                self.log(f"Verbunden @ {self.ser.baudrate}")
            except Exception as e: messagebox.showerror("Fehler", str(e))

    def force_init(self):
        p = self.port_cb.get()
        if self.ser and self.ser.is_open: self.toggle_conn()
        try:
            with serial.Serial(p, 2400, timeout=1) as s:
                s.write(b"W\r")
                self.log(">> W+CR (2400 Bd) gesendet", "out")
        except Exception as e: self.log(f"Fehler: {e}")
        self.toggle_conn()

    def send_full_settings(self):
        cmd = f"SCH={self.sch_cb.get()};RIA={self.ria_cb.get()};KAL={self.kal_cb.get()};SSC={self.ssc_val.get()};"
        self.send_prot(cmd)

    def send_prot(self, payload):
        if not self.ser or not self.ser.is_open: return
        def run():
            try:
                self._stx_received = False
                self.ser.write(ENQ)
                start = time.time()
                while time.time() - start < 1.0:
                    if self._stx_received: break
                    time.sleep(0.01)
                
                cs = self.calc_cs(payload)
                self.ser.write(f"{payload}{cs}\r".encode('ascii'))
                self.log(f">> {payload} (CS: {ord(cs)})", "out")
            except Exception as e: self.log(f"Sende-Fehler: {e}")
        threading.Thread(target=run, daemon=True).start()

    def save_csv(self):
        if not self.shot_results: return
        path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV", "*.csv")])
        if path:
            with open(path, 'w', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=["Zeit", "Nr", "Ring", "Teiler", "Winkel", "Flag"])
                writer.writeheader()
                writer.writerows(self.shot_results)
            messagebox.showinfo("Export", "Gespeichert.")

    def reader(self):
        """Leseschleife mit automatischem ACK."""
        while self.running:
            try:
                if self.ser and self.ser.is_open and self.ser.in_waiting > 0:
                    b = self.ser.read(1)
                    if b == STX: 
                        self._stx_received = True 
                    elif b == ENQ: 
                        # RM will senden -> PC antwortet mit STX [cite: 36]
                        self.ser.write(STX) 
                    elif b == ACK: 
                        self.log("<< ACK erhalten", "in")
                    elif b == NAK:
                        self.log("<< NAK erhalten", "in")
                    else:
                        line_bytes = b + self.ser.readline()
                        # Automatisch ACK senden, sobald eine Nachricht komplett ist 
                        self.ser.write(ACK)
                        
                        line = line_bytes.decode('ascii', errors='replace').strip()
                        if line:
                            self.log(f"<< {line}", "in")
                            if line.startswith("SCH="):
                                # Hier Schussdaten-Parsing Logik einbauen
                                pass
                time.sleep(0.01)
            except: break

if __name__ == "__main__":
    DisagRM3Ultimate().mainloop()