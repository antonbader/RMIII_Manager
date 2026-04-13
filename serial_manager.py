import serial
import threading
import time
import sqlite3
import tkinter as tk

STX, ENQ, ACK, NAK, CR = b'\x02', b'\x05', b'\x06', b'\x15', b'\x0D'

class SerialManager:
    def __init__(self, db_path):
        self.db_path = db_path
        self.ser = None
        self.running = False
        self._stx_received = False
        self._last_status = ""
        self.log_widgets = []

        # Auswertung state
        self.active_entry_id = None
        self.sge_target = 0
        self.current_shots = 0
        self.on_shot_callback = None
        self.on_wsc_error_callback = None

    def add_log_widget(self, widget):
        if widget not in self.log_widgets:
            self.log_widgets.append(widget)

    def is_connected(self):
        return self.ser is not None and self.ser.is_open

    def connect(self, port, baud):
        if self.is_connected():
            self.disconnect()
        self.ser = serial.Serial(port, baud, timeout=0.1)
        self.running = True
        threading.Thread(target=self.reader_loop, daemon=True).start()
        self.log(f"Verbunden mit {port} @ {baud} Baud", "sys")

    def disconnect(self):
        self.running = False
        if self.ser:
            self.ser.close()
            self.ser = None
        self.log("Verbindung getrennt.", "sys")

    def calc_cs(self, data):
        cs = 0
        for char in data: cs ^= ord(char)
        if cs < 32: cs += 32
        return chr(cs)

    def log(self, msg, tag="sys"):
        # Filter spammy WSC status updates
        if "WSC=" in msg:
            if msg == self._last_status: return
            self._last_status = msg

        ts = time.strftime("%H:%M:%S")
        log_line = f"[{ts}] {msg}\n"

        # Update all registered log widgets (Tab 4 and Tab 5) safely in main thread
        for widget in self.log_widgets:
            try:
                widget.after(0, self._append_to_widget, widget, log_line, tag)
            except Exception:
                pass

    def _append_to_widget(self, widget, line, tag):
        widget.configure(state='normal')
        widget.insert("end", line, tag)
        widget.see("end")
        widget.configure(state='disabled')

    def send_prot(self, payload):
        if not self.is_connected(): return
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
            except Exception as e:
                self.log(f"Sende-Fehler: {e}", "err")
        threading.Thread(target=run, daemon=True).start()

    def set_active_auswertung(self, entry_id, sge_target, callback, error_callback=None):
        self.active_entry_id = entry_id
        self.sge_target = sge_target
        self.current_shots = 0
        self.on_shot_callback = callback
        self.on_wsc_error_callback = error_callback
        self.log(f"Auswertung konfiguriert: Eintrag={entry_id}, Max. Schüsse={sge_target}", "sys")

    def parse_and_save_shot(self, line):
        # Format: SCH=Schussnummer;Ringzahl;Teiler; Winkel;Gültigkeit
        # Example: SCH=1;9.0;459.1;18.0;G$
        if not self.active_entry_id:
            return

        try:
            data = line.replace("SCH=", "").split(";")
            if len(data) >= 5:
                schuss_nr = int(data[0])
                ringzahl = float(data[1])
                teiler = float(data[2])
                winkel = float(data[3])

                gueltigkeit_raw = data[4].strip()
                # Parse G, K, U from the first character (ignore checksum chars like $)
                gueltigkeit_char = gueltigkeit_raw[0].upper()
                if gueltigkeit_char == 'G': g_text = "Gültig"
                elif gueltigkeit_char == 'K': g_text = "Kontrolle"
                elif gueltigkeit_char == 'U': g_text = "Ungültig"
                else: g_text = gueltigkeit_raw

                conn = sqlite3.connect(self.db_path)
                c = conn.cursor()
                # Upsert or Insert based on Schuss_nr
                c.execute("SELECT id FROM Ergebnisse WHERE turnier_schuetze_klasse_id=? AND schuss_nr=?", (self.active_entry_id, schuss_nr))
                if c.fetchone():
                    c.execute('''
                        UPDATE Ergebnisse
                        SET ringzahl=?, teiler=?, winkel=?, gueltigkeit=?
                        WHERE turnier_schuetze_klasse_id=? AND schuss_nr=?
                    ''', (ringzahl, teiler, winkel, g_text, self.active_entry_id, schuss_nr))
                else:
                    c.execute('''
                        INSERT INTO Ergebnisse (turnier_schuetze_klasse_id, schuss_nr, ringzahl, teiler, winkel, gueltigkeit)
                        VALUES (?, ?, ?, ?, ?, ?)
                    ''', (self.active_entry_id, schuss_nr, ringzahl, teiler, winkel, g_text))
                    self.current_shots += 1

                conn.commit()
                conn.close()

                self.log(f"Schuss {schuss_nr} gespeichert: {ringzahl} Ringe, Teiler {teiler}", "sys")

                if self.on_shot_callback:
                    # Fire callback to update UI
                    self.on_shot_callback()

                # Check if we reached SGE
                if self.current_shots >= self.sge_target:
                    self.log(f"Auswertung beendet ({self.sge_target} Schüsse erreicht). Nächster Schütze kann ausgewählt werden.", "sys")
                    self.active_entry_id = None

        except Exception as e:
            self.log(f"Fehler beim Parsen des Schusses: {e}", "err")

    def reader_loop(self):
        while self.running:
            try:
                if self.is_connected() and self.ser.in_waiting > 0:
                    b = self.ser.read(1)
                    if b == STX:
                        self._stx_received = True
                    elif b == ENQ:
                        self.ser.write(STX)
                    elif b == ACK:
                        self.log("<< ACK erhalten", "in")
                    elif b == NAK:
                        self.log("<< NAK erhalten", "in")
                    else:
                        line_bytes = b + self.ser.readline()
                        self.ser.write(ACK)
                        line = line_bytes.decode('ascii', errors='replace').strip()
                        # Ignore checksum char at the end of the line if it exists
                        # RM3 Protocol usually appends 1 char CS and CR
                        if len(line) > 0 and line[-1] != ';':
                             line_clean = line[:-1]
                        else:
                             line_clean = line

                        if line_clean:
                            self.log(f"<< {line}", "in")
                            if line.startswith("WSC=1K"):
                                self.log("Gerät ist bereit (WSC=1K). Bitte Scheiben einführen.", "sys")
                            elif line.startswith("SCH="):
                                self.parse_and_save_shot(line_clean)
                            elif line.startswith("WSC=-"):
                                if self.on_wsc_error_callback:
                                    import re
                                    match = re.search(r'WSC=-(\d+)', line_clean)
                                    if match:
                                        num_shots = int(match.group(1))
                                        self.on_wsc_error_callback(line_clean, num_shots)
                time.sleep(0.01)
            except Exception as e:
                self.log(f"Verbindungsfehler im Reader: {e}", "err")
                self.running = False
                break
