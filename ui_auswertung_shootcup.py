import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import sqlite3
import json
import urllib.request
import urllib.parse
import os

from ui_auswertung import WSCErrorWindow

CONFIG_PATH = 'config.json'

class ShootcupPresetWindow(tk.Toplevel):
    def __init__(self, parent, db_path, preset_id, preset_name, callback):
        super().__init__(parent)
        self.db_path = db_path
        self.preset_id = preset_id
        self.callback = callback

        if preset_id:
            self.title(f"Preset bearbeiten: {preset_name}")
        else:
            self.title("Neues Preset erstellen")

        self.geometry("400x350")
        self.grab_set()

        sch, ria, tea, teg, ssc, sge = "LG10", "ZR", "KT", 1000, 1, 40

        if preset_id:
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            c.execute("SELECT sch, ria, tea, teg, ssc, sge FROM Shootcup_Presets WHERE id=?", (preset_id,))
            row = c.fetchone()
            if row:
                sch, ria, tea, teg, ssc, sge = row
            conn.close()

        ttk.Label(self, text="Name:").grid(row=0, column=0, sticky="w", padx=10, pady=5)
        self.en_name = ttk.Entry(self)
        self.en_name.insert(0, preset_name if preset_name else "")
        self.en_name.grid(row=0, column=1, padx=10, pady=5)

        ttk.Label(self, text="Scheibentyp (SCH):").grid(row=1, column=0, sticky="w", padx=10, pady=5)
        self.cb_sch = ttk.Combobox(self, values=["LG10", "LG5", "LGES", "LP"])
        self.cb_sch.set(sch)
        self.cb_sch.grid(row=1, column=1, padx=10, pady=5)

        ttk.Label(self, text="Ringauswertung (RIA):").grid(row=2, column=0, sticky="w", padx=10, pady=5)
        self.cb_ria = ttk.Combobox(self, values=["GR", "ZR", "KR"])
        self.cb_ria.set(ria)
        self.cb_ria.grid(row=2, column=1, padx=10, pady=5)

        ttk.Label(self, text="Teilerauswertung (TEA):").grid(row=3, column=0, sticky="w", padx=10, pady=5)
        self.cb_tea = ttk.Combobox(self, values=["KT", "ZT"])
        self.cb_tea.set(tea)
        self.cb_tea.grid(row=3, column=1, padx=10, pady=5)

        ttk.Label(self, text="Teilergrenze (TEG):").grid(row=4, column=0, sticky="w", padx=10, pady=5)
        self.sb_teg = ttk.Spinbox(self, from_=100, to=4000)
        self.sb_teg.set(teg)
        self.sb_teg.grid(row=4, column=1, padx=10, pady=5)

        ttk.Label(self, text="Schusszahl/Scheibe (SSC):").grid(row=5, column=0, sticky="w", padx=10, pady=5)
        self.sb_ssc = ttk.Spinbox(self, from_=1, to=10)
        self.sb_ssc.set(ssc)
        self.sb_ssc.grid(row=5, column=1, padx=10, pady=5)

        ttk.Label(self, text="Schusszahl Gesamt (SGE):").grid(row=6, column=0, sticky="w", padx=10, pady=5)
        self.sb_sge = ttk.Spinbox(self, from_=1, to=120)
        self.sb_sge.set(sge)
        self.sb_sge.grid(row=6, column=1, padx=10, pady=5)

        ttk.Button(self, text="Speichern", command=self.save).grid(row=7, column=0, columnspan=2, pady=15)

    def save(self):
        name = self.en_name.get().strip()
        if not name:
            messagebox.showerror("Fehler", "Bitte einen Namen eingeben.")
            return

        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()

        if self.preset_id:
            c.execute('''
                UPDATE Shootcup_Presets
                SET name=?, sch=?, ria=?, tea=?, teg=?, ssc=?, sge=?
                WHERE id=?
            ''', (name, self.cb_sch.get(), self.cb_ria.get(), self.cb_tea.get(), self.sb_teg.get(), self.sb_ssc.get(), self.sb_sge.get(), self.preset_id))
        else:
            c.execute('''
                INSERT INTO Shootcup_Presets (name, sch, ria, tea, teg, ssc, sge)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (name, self.cb_sch.get(), self.cb_ria.get(), self.cb_tea.get(), self.sb_teg.get(), self.sb_ssc.get(), self.sb_sge.get()))

        conn.commit()
        conn.close()
        self.callback()
        self.destroy()

class AuswertungShootcupUI(ttk.Frame):
    def __init__(self, parent, db_path, serial_manager):
        super().__init__(parent)
        self.db_path = db_path
        self.serial_manager = serial_manager



        # TOP FRAME: Shootcup Settings
        top_frame = ttk.LabelFrame(self, text="Shootcup Konfiguration", padding=10)
        top_frame.pack(fill="x", pady=5)

        # Shooter Name
        ttk.Label(top_frame, text="Schütze:").grid(row=0, column=0, sticky="w", padx=5, pady=5)
        self.en_schuetze = ttk.Entry(top_frame, width=30)
        self.en_schuetze.grid(row=0, column=1, sticky="w", padx=5, pady=5)

        # Evaluation Type
        ttk.Label(top_frame, text="Auswertung auf:").grid(row=0, column=2, sticky="w", padx=5, pady=5)
        self.cb_type = ttk.Combobox(top_frame, state="readonly", values=["ringzahl", "teiler"], width=15)
        self.cb_type.set("ringzahl")
        self.cb_type.grid(row=0, column=3, sticky="w", padx=5, pady=5)

        # Preset Selection
        ttk.Label(top_frame, text="Preset:").grid(row=1, column=0, sticky="w", padx=5, pady=5)
        self.cb_presets = ttk.Combobox(top_frame, state="readonly", width=30)
        self.cb_presets.grid(row=1, column=1, sticky="w", padx=5, pady=5)

        # Preset Buttons
        btn_f = ttk.Frame(top_frame)
        btn_f.grid(row=1, column=2, columnspan=2, sticky="w", padx=5, pady=5)
        ttk.Button(btn_f, text="Neu", command=self.new_preset).pack(side="left", padx=2)
        ttk.Button(btn_f, text="Bearbeiten", command=self.edit_preset).pack(side="left", padx=2)
        ttk.Button(btn_f, text="Löschen", command=self.delete_preset).pack(side="left", padx=2)

        self.load_presets()

        # ACTION BUTTONS
        act_frame = ttk.Frame(self)
        act_frame.pack(fill="x", pady=5)

        self.btn_start = ttk.Button(act_frame, text="Auswertung starten", command=self.start_auswertung)
        self.btn_start.pack(side="left", padx=5)

        self.btn_transmit = ttk.Button(act_frame, text="Übertragen", state="disabled", command=self.transmit_results)
        self.btn_transmit.pack(side="right", padx=5)

        # MIDDLE FRAME: Results
        res_frame = ttk.LabelFrame(self, text="Ergebnisse", padding=5)
        res_frame.pack(fill="both", expand=True, pady=5)

        self.tree_res = ttk.Treeview(res_frame, columns=("Schuss", "Ringzahl", "Teiler", "Winkel", "Gültigkeit"), show="headings")
        for col in self.tree_res["columns"]:
            self.tree_res.heading(col, text=col)
            self.tree_res.column(col, anchor="center", width=80)
        self.tree_res.pack(fill="both", expand=True, pady=5)

        # SUMMARY FRAME
        self.summary_frame = ttk.Frame(res_frame)
        self.summary_frame.pack(fill="x", pady=5)

        self.lbl_sum_rings_text = ttk.Label(self.summary_frame, text="Summe Ringzahlen:", font=("Helvetica", 10, "bold"))
        self.lbl_sum_rings_text.pack(side="left", padx=(5, 2))
        self.lbl_sum_rings_val = ttk.Label(self.summary_frame, text="-", font=("Helvetica", 10))
        self.lbl_sum_rings_val.pack(side="left", padx=(0, 15))

        self.lbl_best_teiler_text = ttk.Label(self.summary_frame, text="Bester Teiler:", font=("Helvetica", 10, "bold"))
        self.lbl_best_teiler_text.pack(side="left", padx=(5, 2))
        self.lbl_best_teiler_val = ttk.Label(self.summary_frame, text="-", font=("Helvetica", 10))
        self.lbl_best_teiler_val.pack(side="left", padx=(0, 5))

        self.create_config_if_missing()

    def create_config_if_missing(self):
        if not os.path.exists(CONFIG_PATH):
            with open(CONFIG_PATH, 'w') as f:
                json.dump({"shootcup_api_url": "http://localhost:5003/api/score"}, f, indent=4)

    def load_presets(self):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("SELECT id, name FROM Shootcup_Presets ORDER BY name")
        self.presets = c.fetchall()
        conn.close()

        values = [p[1] for p in self.presets]
        self.cb_presets['values'] = values
        if values:
            self.cb_presets.current(0)
        else:
            self.cb_presets.set("")

    def get_selected_preset_id(self):
        idx = self.cb_presets.current()
        if idx >= 0:
            return self.presets[idx][0]
        return None

    def new_preset(self):
        ShootcupPresetWindow(self, self.db_path, None, "", self.load_presets)

    def edit_preset(self):
        p_id = self.get_selected_preset_id()
        if not p_id:
            return
        p_name = self.presets[self.cb_presets.current()][1]
        ShootcupPresetWindow(self, self.db_path, p_id, p_name, self.load_presets)

    def delete_preset(self):
        p_id = self.get_selected_preset_id()
        if not p_id:
            return
        p_name = self.presets[self.cb_presets.current()][1]

        if messagebox.askyesno("Löschen", f"Preset '{p_name}' wirklich löschen?"):
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            c.execute("DELETE FROM Shootcup_Presets WHERE id=?", (p_id,))
            conn.commit()
            conn.close()
            self.load_presets()

    def start_auswertung(self):
        if not self.serial_manager.is_connected():
            messagebox.showerror("Fehler", "Bitte zuerst im Reiter 'Verbindung' eine Verbindung herstellen.")
            return

        p_id = self.get_selected_preset_id()
        if not p_id:
            messagebox.showerror("Fehler", "Bitte ein Preset auswählen.")
            return

        schuetze = self.en_schuetze.get().strip()
        if not schuetze:
            messagebox.showerror("Fehler", "Bitte einen Schützen eingeben.")
            return

        # Clear old temporary results
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("DELETE FROM Shootcup_Ergebnisse")

        # Get preset config
        c.execute("SELECT sch, ria, tea, teg, ssc, sge FROM Shootcup_Presets WHERE id=?", (p_id,))
        row = c.fetchone()
        conn.commit()
        conn.close()

        if not row:
            return

        sch, ria, tea, teg, ssc, sge = row
        self.sge_target = sge

        # SZI=0 and KAL=22 are fixed
        cmd = f"SCH={sch};RIA={ria};KAL=22;SSC={ssc};SZI=0;TEA={tea};TEG={teg};SGE={sge};"

        # Use -1 as entry_id since we are not linking to a tournament structure
        # Pass is_shootcup=True to use the temp table
        self.serial_manager.set_active_auswertung(-1, self.sge_target, self.on_shot_received, self.on_wsc_error, is_shootcup=True)

        self.serial_manager.log(f"Starte Shootcup Auswertung für {schuetze}. Sende Konfiguration...")
        self.serial_manager.send_prot(cmd)

        self.load_results()
        self.btn_transmit.config(state="normal")

    def on_wsc_error(self, wsc_code, num_shots):
        self.after(0, lambda: WSCErrorWindow(self, self.db_path, self.serial_manager, -1, wsc_code, num_shots, self.on_shot_received, is_shootcup=True))

    def on_shot_received(self):
        self.after(0, self.load_results)

    def load_results(self):
        for i in self.tree_res.get_children(): self.tree_res.delete(i)

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT schuss_nr, ringzahl, teiler, winkel, gueltigkeit
            FROM Shootcup_Ergebnisse
            ORDER BY schuss_nr ASC
        ''')

        for row in cursor.fetchall():
            self.tree_res.insert("", "end", values=row)

        cursor.execute('''
            SELECT SUM(ringzahl), MIN(teiler)
            FROM Shootcup_Ergebnisse
        ''')
        row = cursor.fetchone()
        conn.close()

        sum_rings_str, best_teiler_str = "-", "-"
        if row:
            sum_rings, best_teiler = row
            if sum_rings is not None:
                sum_rings_str = f"{sum_rings:.1f}".replace('.', ',')
            if best_teiler is not None:
                best_teiler_str = f"{best_teiler:.1f}".replace('.', ',')

        self.lbl_sum_rings_val.config(text=sum_rings_str)
        self.lbl_best_teiler_val.config(text=best_teiler_str)

    def transmit_results(self):
        schuetze = self.en_schuetze.get().strip()
        auswertung_type = self.cb_type.get()
        klasse = self.presets[self.cb_presets.current()][1] if self.get_selected_preset_id() else ""

        if not schuetze:
            messagebox.showerror("Fehler", "Schützenname fehlt.")
            return

        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute('SELECT schuss_nr, ringzahl, teiler FROM Shootcup_Ergebnisse ORDER BY schuss_nr ASC')
        shots = c.fetchall()

        c.execute('SELECT SUM(ringzahl) FROM Shootcup_Ergebnisse')
        sum_row = c.fetchone()
        sum_rings = sum_row[0] if sum_row and sum_row[0] is not None else 0.0
        conn.close()

        if not shots:
            messagebox.showinfo("Info", "Es gibt keine Ergebnisse zum Übertragen.")
            return

        # Load API URL from config
        api_url = "http://localhost:5003/api/score"
        try:
            if os.path.exists(CONFIG_PATH):
                with open(CONFIG_PATH, 'r') as f:
                    config = json.load(f)
                    api_url = config.get("shootcup_api_url", api_url)
        except Exception as e:
            print(f"Failed to load config.json: {e}")

        # Send data
        try:
            if auswertung_type == "ringzahl":
                data = {
                    "name": schuetze,
                    "scores": [float(sum_rings)],
                    "type": "ringzahl",
                    "klasse": klasse
                }
                self.send_post(api_url, data)
            else: # teiler
                teiler_list = [float(shot[2]) for shot in shots]
                data = {
                    "name": schuetze,
                    "scores": teiler_list,
                    "type": "teiler",
                    "klasse": klasse
                }
                self.send_post(api_url, data)

            messagebox.showinfo("Erfolg", "Ergebnisse wurden erfolgreich übertragen.")

            # Clear data after successful transmission
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            c.execute("DELETE FROM Shootcup_Ergebnisse")
            conn.commit()
            conn.close()
            self.load_results()
            self.btn_transmit.config(state="disabled")

        except Exception as e:
            messagebox.showerror("Fehler", f"Fehler bei der Übertragung:\n{str(e)}")

    def send_post(self, url, data):
        req = urllib.request.Request(url)
        req.add_header('Content-Type', 'application/json; charset=utf-8')
        jsondata = json.dumps(data).encode('utf-8')
        req.add_header('Content-Length', len(jsondata))

        response = urllib.request.urlopen(req, jsondata)
        if response.status not in (200, 201):
            raise Exception(f"HTTP Status {response.status}: {response.read().decode('utf-8')}")
