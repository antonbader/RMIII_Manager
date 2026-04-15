import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import sqlite3
import pandas as pd
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import time

class AuswertungUI(ttk.Frame):
    def __init__(self, parent, db_path, serial_manager):
        super().__init__(parent)
        self.db_path = db_path
        self.serial_manager = serial_manager

        self.pack(fill="both", expand=True, padx=10, pady=10)

        # TOP FRAME: Select Tournament
        top_frame = ttk.LabelFrame(self, text="Turnierauswahl", padding=10)
        top_frame.pack(fill="x", pady=5)

        ttk.Label(top_frame, text="Turnier:").pack(side="left", padx=5)
        self.cb_turniere = ttk.Combobox(top_frame, state="readonly", width=40)
        self.cb_turniere.pack(side="left", padx=5)
        self.cb_turniere.bind("<<ComboboxSelected>>", self.on_turnier_selected)

        ttk.Button(top_frame, text="Turniere laden", command=self.load_turniere).pack(side="left", padx=5)

        # MIDDLE FRAME (Paned Window)
        self.paned = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        self.paned.pack(fill="both", expand=True, pady=5)

        # LEFT SIDE: Participants (Shooter + Class)
        left_frame = ttk.LabelFrame(self.paned, text="Teilnehmer (Schütze - Klasse)", padding=5)
        self.paned.add(left_frame, weight=1)

        search_f = ttk.Frame(left_frame)
        search_f.pack(fill="x")
        ttk.Label(search_f, text="Suchen/Filtern:").pack(side="left", padx=2)
        self.search_part_var = tk.StringVar()
        self.search_part_var.trace_add("write", lambda *args: self.load_participants())
        ttk.Entry(search_f, textvariable=self.search_part_var).pack(side="left", fill="x", expand=True, padx=2)

        self.tree_part = ttk.Treeview(left_frame, columns=("ID", "Schütze", "Klasse", "K_ID"), show="headings", selectmode="browse")
        self.tree_part.heading("Schütze", text="Schütze", command=lambda: self.sort_part_column("Schütze", False))
        self.tree_part.heading("Klasse", text="Klasse", command=lambda: self.sort_part_column("Klasse", False))
        self.tree_part.column("ID", width=0, stretch=False)
        self.tree_part.column("K_ID", width=0, stretch=False)
        self.tree_part.pack(fill="both", expand=True, pady=5)
        self.tree_part.bind("<<TreeviewSelect>>", self.on_participant_selected)

        self.btn_start = ttk.Button(left_frame, text="Auswertung starten", state="disabled", command=self.start_auswertung)
        self.btn_start.pack(fill="x", pady=5)

        self.btn_show_all = ttk.Button(left_frame, text="Alle anzeigen", state="disabled", command=self.show_all_results)
        self.btn_show_all.pack(fill="x", pady=5)

        # RIGHT SIDE: Results
        right_frame = ttk.LabelFrame(self.paned, text="Ergebnisse", padding=5)
        self.paned.add(right_frame, weight=2)

        res_search_f = ttk.Frame(right_frame)
        res_search_f.pack(fill="x")
        ttk.Label(res_search_f, text="Suchen/Filtern:").pack(side="left", padx=2)
        self.search_res_var = tk.StringVar()
        self.search_res_var.trace_add("write", lambda *args: self.load_results())
        ttk.Entry(res_search_f, textvariable=self.search_res_var).pack(side="left", fill="x", expand=True, padx=2)

        self.tree_res = ttk.Treeview(right_frame, columns=("Name", "Klasse", "Schuss", "Ringzahl", "Teiler", "Winkel", "Gültigkeit"), show="headings")
        for col in self.tree_res["columns"]:
            self.tree_res.heading(col, text=col, command=lambda c=col: self.sort_res_column(c, False))
            self.tree_res.column(col, anchor="center", width=80)
        self.tree_res.column("Name", width=120)
        self.tree_res.column("Klasse", width=100)
        self.tree_res.pack(fill="both", expand=True, pady=5)

        export_f = ttk.Frame(right_frame)
        export_f.pack(fill="x")
        ttk.Button(export_f, text="Export Excel", command=self.export_excel).pack(side="right", padx=5)
        ttk.Button(export_f, text="Export PDF", command=self.export_pdf).pack(side="right", padx=5)

        # SUMMARY FRAME (Sum of rings, best teiler)
        self.summary_frame = ttk.Frame(right_frame)
        self.summary_frame.pack(fill="x", pady=5)

        self.lbl_sum_rings_text = ttk.Label(self.summary_frame, text="Summe Ringzahlen:", font=("Helvetica", 10, "bold"))
        self.lbl_sum_rings_text.pack(side="left", padx=(5, 2))
        self.lbl_sum_rings_val = ttk.Label(self.summary_frame, text="-", font=("Helvetica", 10))
        self.lbl_sum_rings_val.pack(side="left", padx=(0, 15))

        self.lbl_best_teiler_text = ttk.Label(self.summary_frame, text="Bester Teiler:", font=("Helvetica", 10, "bold"))
        self.lbl_best_teiler_text.pack(side="left", padx=(5, 2))
        self.lbl_best_teiler_val = ttk.Label(self.summary_frame, text="-", font=("Helvetica", 10))
        self.lbl_best_teiler_val.pack(side="left", padx=(0, 5))

        # BOTTOM FRAME: Log
        log_frame = ttk.LabelFrame(self, text="Kommunikation mit DISAG RM III", padding=5)
        log_frame.pack(fill="x", pady=5)
        self.txt_log = tk.Text(log_frame, height=8, state="disabled", bg="#1e1e1e", fg="#d4d4d4", font=("Consolas", 10))
        self.txt_log.pack(fill="both", expand=True)
        self.txt_log.tag_config("in", foreground="#b5cea8")
        self.txt_log.tag_config("out", foreground="#569cd6")
        self.txt_log.tag_config("sys", foreground="#ce9178")
        self.txt_log.tag_config("err", foreground="#f44747")

        self.serial_manager.add_log_widget(self.txt_log)

        self.current_turnier_id = None
        self.active_entry_id = None
        self.active_klasse_id = None
        self.sge_target = 0
        self.current_shots = 0
        self.show_all_mode = False

    def get_db_connection(self):
        return sqlite3.connect(self.db_path)

    def load_turniere(self):
        conn = self.get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, name FROM Turniere ORDER BY id DESC")
        self.turniere_data = cursor.fetchall()
        conn.close()

        values = [f"{t[0]} - {t[1]}" for t in self.turniere_data]
        self.cb_turniere.config(values=values)
        if values:
            self.cb_turniere.set(values[0])
            self.on_turnier_selected()

    def on_turnier_selected(self, event=None):
        sel = self.cb_turniere.get()
        if not sel: return
        self.current_turnier_id = int(sel.split(" - ")[0])
        self.show_all_mode = False
        self.load_participants()
        self.btn_start.config(state="disabled")
        self.btn_show_all.config(state="normal")
        for i in self.tree_res.get_children(): self.tree_res.delete(i)

    def load_participants(self):
        if not self.current_turnier_id: return
        for i in self.tree_part.get_children(): self.tree_part.delete(i)

        st = f"%{self.search_part_var.get()}%"
        conn = self.get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT tsk.id, s.name, k.name, k.id
            FROM Turnier_Schuetzen_Klassen tsk
            JOIN Schuetzen s ON tsk.schuetze_id = s.id
            JOIN Klassen k ON tsk.klasse_id = k.id
            WHERE tsk.turnier_id = ? AND (s.name LIKE ? OR k.name LIKE ?)
        ''', (self.current_turnier_id, st, st))

        for row in cursor.fetchall():
            self.tree_part.insert("", "end", values=row)
        conn.close()

    def sort_part_column(self, col, reverse):
        l = [(self.tree_part.set(k, col), k) for k in self.tree_part.get_children('')]
        try: l.sort(key=lambda t: float(t[0]), reverse=reverse)
        except ValueError: l.sort(reverse=reverse)
        for index, (val, k) in enumerate(l): self.tree_part.move(k, '', index)
        self.tree_part.heading(col, command=lambda: self.sort_part_column(col, not reverse))

    def on_participant_selected(self, event=None):
        sel = self.tree_part.selection()
        if not sel:
            self.btn_start.config(state="disabled")
            return
        vals = self.tree_part.item(sel[0])['values']
        self.active_entry_id = vals[0]
        self.active_klasse_id = vals[3]
        self.show_all_mode = False
        self.btn_start.config(state="normal")
        self.load_results()

    def show_all_results(self):
        if not self.current_turnier_id: return
        self.show_all_mode = True
        self.load_results()

    def start_auswertung(self):
        if not self.serial_manager.is_connected():
            messagebox.showerror("Fehler", "Gerät ist nicht verbunden! Bitte im Reiter 'Verbindung' verbinden.")
            return

        # Fetch settings for this class
        conn = self.get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT sch, ria, tea, teg, ssc, sge
            FROM Turnier_Klassen
            WHERE turnier_id=? AND klasse_id=?
        ''', (self.current_turnier_id, self.active_klasse_id))
        row = cursor.fetchone()
        conn.close()

        if not row:
            messagebox.showerror("Fehler", "Einstellungen für diese Klasse nicht gefunden.")
            return

        sch, ria, tea, teg, ssc, sge = row
        self.sge_target = sge
        self.current_shots = 0

        # Send configuration to device
        # SZI=0 and KAL=22 are fixed values as per instructions
        cmd = f"SCH={sch};RIA={ria};KAL=22;SSC={ssc};SZI=0;TEA={tea};TEG={teg};SGE={sge};"

        # We need to configure the serial manager to handle the incoming shot data and save it to DB
        self.serial_manager.set_active_auswertung(self.active_entry_id, self.sge_target, self.on_shot_received, self.on_wsc_error)

        self.serial_manager.log(f"Starte Auswertung für Eintrag ID {self.active_entry_id}. Sende Konfiguration...")
        self.serial_manager.send_prot(cmd)

    def on_wsc_error(self, wsc_code, num_shots):
        self.after(0, lambda: WSCErrorWindow(self, self.db_path, self.serial_manager, self.active_entry_id, wsc_code, num_shots, self.on_shot_received))

    def on_shot_received(self):
        # Callback from Serial Manager when a shot is successfully parsed and saved to DB
        # This is called from a background thread, so we must use after() to update the UI
        self.after(0, self.load_results)

    def load_results(self):
        for i in self.tree_res.get_children(): self.tree_res.delete(i)

        st = f"%{self.search_res_var.get()}%"
        conn = self.get_db_connection()
        cursor = conn.cursor()

        if self.show_all_mode:
            if not self.current_turnier_id: return
            cursor.execute('''
                SELECT s.name, k.name, e.schuss_nr, e.ringzahl, e.teiler, e.winkel, e.gueltigkeit
                FROM Ergebnisse e
                JOIN Turnier_Schuetzen_Klassen tsk ON e.turnier_schuetze_klasse_id = tsk.id
                JOIN Schuetzen s ON tsk.schuetze_id = s.id
                JOIN Klassen k ON tsk.klasse_id = k.id
                WHERE tsk.turnier_id = ?
                AND (s.name LIKE ? OR k.name LIKE ? OR e.schuss_nr LIKE ? OR e.ringzahl LIKE ? OR e.teiler LIKE ? OR e.gueltigkeit LIKE ?)
                ORDER BY e.id ASC
            ''', (self.current_turnier_id, st, st, st, st, st, st))
        else:
            if not self.active_entry_id: return
            cursor.execute('''
                SELECT s.name, k.name, e.schuss_nr, e.ringzahl, e.teiler, e.winkel, e.gueltigkeit
                FROM Ergebnisse e
                JOIN Turnier_Schuetzen_Klassen tsk ON e.turnier_schuetze_klasse_id = tsk.id
                JOIN Schuetzen s ON tsk.schuetze_id = s.id
                JOIN Klassen k ON tsk.klasse_id = k.id
                WHERE e.turnier_schuetze_klasse_id = ?
                AND (s.name LIKE ? OR k.name LIKE ? OR e.schuss_nr LIKE ? OR e.ringzahl LIKE ? OR e.teiler LIKE ? OR e.gueltigkeit LIKE ?)
                ORDER BY e.schuss_nr ASC
            ''', (self.active_entry_id, st, st, st, st, st, st))

        for row in cursor.fetchall():
            self.tree_res.insert("", "end", values=row)
        conn.close()

        self.update_summary()

    def update_summary(self):
        # Default to '-'
        sum_rings_str = "-"
        best_teiler_str = "-"

        # Only calculate if we are viewing a single participant's results
        if not self.show_all_mode and self.active_entry_id:
            conn = self.get_db_connection()
            cursor = conn.cursor()
            cursor.execute('''
                SELECT SUM(ringzahl), MIN(teiler)
                FROM Ergebnisse
                WHERE turnier_schuetze_klasse_id = ?
            ''', (self.active_entry_id,))
            row = cursor.fetchone()
            conn.close()

            if row:
                sum_rings, best_teiler = row
                if sum_rings is not None:
                    # Format with comma as decimal separator
                    sum_rings_str = f"{sum_rings:.1f}".replace('.', ',')
                if best_teiler is not None:
                    best_teiler_str = f"{best_teiler:.1f}".replace('.', ',')

        self.lbl_sum_rings_val.config(text=sum_rings_str)
        self.lbl_best_teiler_val.config(text=best_teiler_str)

    def sort_res_column(self, col, reverse):
        l = [(self.tree_res.set(k, col), k) for k in self.tree_res.get_children('')]
        try: l.sort(key=lambda t: float(t[0]), reverse=reverse)
        except ValueError: l.sort(reverse=reverse)
        for index, (val, k) in enumerate(l): self.tree_res.move(k, '', index)
        self.tree_res.heading(col, command=lambda: self.sort_res_column(col, not reverse))

    def get_res_data_as_df(self):
        # Fetch current data from treeview considering filters and sorting
        data = []
        for i in self.tree_res.get_children():
            data.append(self.tree_res.item(i)['values'])
        cols = ["Name", "Klasse", "Schuss", "Ringzahl", "Teiler", "Winkel", "Gültigkeit"]
        return pd.DataFrame(data, columns=cols)

    def export_excel(self):
        if self.show_all_mode:
            # Ask user if they want summary or detailed export
            answer = messagebox.askyesnocancel("Export",
                                               "Möchten Sie eine Zusammenfassung (Summe Ringe & Bester Teiler pro Schütze/Klasse) exportieren?\n\n"
                                               "'Ja' = Zusammenfassung exportieren\n"
                                               "'Nein' = Detaillierte Einzelergebnisse exportieren\n"
                                               "'Abbrechen' = Export abbrechen")
            if answer is None:
                return
            elif answer is True:
                self.export_excel_summary()
                return

        df = self.get_res_data_as_df()
        if df.empty:
            messagebox.showinfo("Export", "Keine Daten zum Exportieren vorhanden.")
            return

        path = filedialog.asksaveasfilename(defaultextension=".xlsx", filetypes=[("Excel", "*.xlsx")])
        if path:
            self.format_df_german_locale(df)
            df.to_excel(path, index=False)
            messagebox.showinfo("Export", f"Erfolgreich als Excel gespeichert:\n{path}")

    def export_excel_summary(self):
        if not self.current_turnier_id:
            messagebox.showinfo("Export", "Kein Turnier ausgewählt.")
            return

        # Fetch all results for current turnier
        conn = self.get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT s.name, k.name, e.ringzahl, e.teiler
            FROM Ergebnisse e
            JOIN Turnier_Schuetzen_Klassen tsk ON e.turnier_schuetze_klasse_id = tsk.id
            JOIN Schuetzen s ON tsk.schuetze_id = s.id
            JOIN Klassen k ON tsk.klasse_id = k.id
            WHERE tsk.turnier_id = ?
        ''', (self.current_turnier_id,))
        rows = cursor.fetchall()
        conn.close()

        if not rows:
            messagebox.showinfo("Export", "Keine Daten zum Exportieren vorhanden.")
            return

        # Use pandas to group by Shooter and Class
        df = pd.DataFrame(rows, columns=["Schütze", "Klasse", "Ringzahl", "Teiler"])

        # We need to calculate Sum of Ringzahl and Min of Teiler
        summary_df = df.groupby(["Schütze", "Klasse"]).agg(
            Summe_Ringzahlen=("Ringzahl", "sum"),
            Bester_Teiler=("Teiler", "min")
        ).reset_index()

        path = filedialog.asksaveasfilename(defaultextension=".xlsx", filetypes=[("Excel", "*.xlsx")])
        if path:
            self.format_df_german_locale(summary_df)
            summary_df.to_excel(path, index=False)
            messagebox.showinfo("Export", f"Erfolgreich als Zusammenfassung in Excel gespeichert:\n{path}")

    def format_df_german_locale(self, df):
        # Replace dot with comma for all float columns to match German locale
        for col in df.select_dtypes(include=['float64', 'float32']).columns:
            df[col] = df[col].apply(lambda x: f"{x:.1f}".replace('.', ',') if pd.notnull(x) else x)

        # Also convert any string representations that might be numeric
        for col in df.columns:
            # We also check for int and float that might have been loaded by pandas or converted to string from treeview
            df[col] = df[col].apply(lambda x: self.format_value(x))

    def format_value(self, x):
        if pd.isnull(x):
            return x
        if isinstance(x, float):
            return f"{x:.1f}".replace('.', ',')
        if isinstance(x, str):
            if self.is_float_string(x):
                return x.replace('.', ',')
        return x

    def is_float_string(self, s):
        try:
            float(s)
            return '.' in s
        except ValueError:
            return False

    def export_pdf(self):
        df = self.get_res_data_as_df()
        if df.empty:
            messagebox.showinfo("Export", "Keine Daten zum Exportieren vorhanden.")
            return

        path = filedialog.asksaveasfilename(defaultextension=".pdf", filetypes=[("PDF", "*.pdf")])
        if path:
            c = canvas.Canvas(path, pagesize=letter)
            c.setFont("Helvetica-Bold", 14)
            c.drawString(50, 750, "Auswertung - DISAG RM III")

            # Additional metadata if possible
            sel = self.tree_part.selection()
            if sel:
                vals = self.tree_part.item(sel[0])['values']
                c.setFont("Helvetica", 12)
                c.drawString(50, 730, f"Schütze: {vals[1]} | Klasse: {vals[2]}")

            c.setFont("Helvetica-Bold", 10)
            y = 700
            cols = ["Name", "Klasse", "Schuss", "Ringzahl", "Teiler", "Winkel", "Gültigkeit"]
            x_pos = [50, 150, 230, 290, 360, 420, 480]

            for i, col in enumerate(cols):
                c.drawString(x_pos[i], y, col)

            y -= 20
            c.setFont("Helvetica", 10)

            for index, row in df.iterrows():
                for i, val in enumerate(row):
                    c.drawString(x_pos[i], y, str(val))
                y -= 15
                if y < 50:
                    c.showPage()
                    y = 750
                    c.setFont("Helvetica", 10)

            c.save()
            messagebox.showinfo("Export", f"Erfolgreich als PDF gespeichert:\n{path}")


class WSCErrorWindow(tk.Toplevel):
    def __init__(self, parent, db_path, serial_manager, entry_id, wsc_code, num_shots, callback, is_shootcup=False):
        super().__init__(parent)
        self.db_path = db_path
        self.serial_manager = serial_manager
        self.entry_id = entry_id
        self.num_shots = num_shots
        self.callback = callback
        self.is_shootcup = is_shootcup

        self.title("Überprüfung nötig")
        self.geometry("400x350")
        self.grab_set()

        ttk.Label(self, text=f"Das Gerät meldet einen Fehler: {wsc_code}", font=("Helvetica", 10, "bold")).pack(pady=15)
        ttk.Label(self, text="Bitte wählen Sie das weitere Vorgehen:").pack(pady=5)

        ttk.Button(self, text="Wiederholen", command=self.do_wiederholen, width=30).pack(pady=10)
        ttk.Button(self, text="Auswertung abbrechen und löschen", command=self.do_abbrechen, width=30).pack(pady=10)
        ttk.Button(self, text="Kontrolle", command=self.do_kontrolle, width=30).pack(pady=10)
        ttk.Button(self, text="Alles OK", command=self.do_alles_ok, width=30).pack(pady=10)

    def get_last_target_shots(self):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()

        if self.is_shootcup:
            c.execute('''
                SELECT id, schuss_nr, ringzahl, teiler, gueltigkeit
                FROM Shootcup_Ergebnisse
                ORDER BY schuss_nr DESC
                LIMIT ?
            ''', (self.num_shots,))
            last_n_shots = c.fetchall()
            c.execute('SELECT COUNT(*) FROM Shootcup_Ergebnisse')
            total_shots = c.fetchone()[0]
        else:
            # Get the last `num_shots` for this shooter
            c.execute('''
                SELECT id, schuss_nr, ringzahl, teiler, gueltigkeit
                FROM Ergebnisse
                WHERE turnier_schuetze_klasse_id=?
                ORDER BY schuss_nr DESC
                LIMIT ?
            ''', (self.entry_id, self.num_shots))
            last_n_shots = c.fetchall()
            c.execute('SELECT COUNT(*) FROM Ergebnisse WHERE turnier_schuetze_klasse_id=?', (self.entry_id,))
            total_shots = c.fetchone()[0]

        # We need them in ascending order and only those that are NOT 'Gültig'
        shots = sorted([s for s in last_n_shots if s[4] != 'Gültig'], key=lambda x: x[1])
        conn.close()
        return shots, total_shots

    def do_wiederholen(self):
        self.serial_manager.send_prot("WID")
        self.destroy()

    def do_abbrechen(self):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        if self.is_shootcup:
            c.execute("DELETE FROM Shootcup_Ergebnisse")
        else:
            c.execute("DELETE FROM Ergebnisse WHERE turnier_schuetze_klasse_id=?", (self.entry_id,))
        conn.commit()
        conn.close()
        self.serial_manager.send_prot("ABR")
        self.callback()
        self.destroy()

    def do_alles_ok(self):
        shots, total_shots = self.get_last_target_shots()
        if not shots:
            self.serial_manager.send_prot("EDI=0;0")
        else:
            edi_cmd = f"EDI={total_shots};{len(shots)}"
            self.serial_manager.send_prot(edi_cmd)

            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()

            if self.is_shootcup:
                c.execute('''
                    SELECT id, schuss_nr, ringzahl, teiler
                    FROM Shootcup_Ergebnisse
                    ORDER BY schuss_nr ASC
                ''')
            else:
                # Fetch ALL shots for this shooter to send them back to the device
                c.execute('''
                    SELECT id, schuss_nr, ringzahl, teiler
                    FROM Ergebnisse
                    WHERE turnier_schuetze_klasse_id=?
                    ORDER BY schuss_nr ASC
                ''', (self.entry_id,))

            all_shots = c.fetchall()

            # Track which ones are the "last targets" to update their status
            last_target_ids = {s[0] for s in shots}

            for shot in all_shots:
                shot_id, schuss_nr, ringzahl, teiler = shot
                # All shots (old and new unchanged) get 'U'
                s_cmd = f"S={schuss_nr};{ringzahl};{teiler};U"
                self.serial_manager.send_prot(s_cmd)

                # Only update the database status for the recently checked ones
                if shot_id in last_target_ids:
                    if self.is_shootcup:
                        c.execute("UPDATE Shootcup_Ergebnisse SET gueltigkeit='Überprüft' WHERE id=?", (shot_id,))
                    else:
                        c.execute("UPDATE Ergebnisse SET gueltigkeit='Überprüft' WHERE id=?", (shot_id,))

            conn.commit()
            conn.close()

        self.callback()
        self.destroy()

    def do_kontrolle(self):
        shots, total_shots = self.get_last_target_shots()
        self.destroy()
        KontrolleWindow(self.master, self.db_path, self.serial_manager, self.entry_id, shots, total_shots, self.callback, self.is_shootcup)


class KontrolleWindow(tk.Toplevel):
    def __init__(self, parent, db_path, serial_manager, entry_id, shots, total_shots, callback, is_shootcup=False):
        super().__init__(parent)
        self.db_path = db_path
        self.serial_manager = serial_manager
        self.entry_id = entry_id
        self.shots = shots
        self.total_shots = total_shots
        self.callback = callback
        self.is_shootcup = is_shootcup
        self.entries = []

        self.title("Manuelle Kontrolle")
        self.geometry("500x400")
        self.grab_set()

        if not self.shots:
            ttk.Label(self, text="Keine zu überprüfenden Schüsse gefunden.").pack(pady=20)
            ttk.Button(self, text="Schließen", command=self.destroy).pack()
            return

        frame = ttk.Frame(self)
        frame.pack(fill="both", expand=True, padx=10, pady=10)

        ttk.Label(frame, text="Schuss").grid(row=0, column=0, padx=5, pady=5)
        ttk.Label(frame, text="Ringwert").grid(row=0, column=1, padx=5, pady=5)
        ttk.Label(frame, text="Teilerwert").grid(row=0, column=2, padx=5, pady=5)

        for i, shot in enumerate(self.shots):
            shot_id, schuss_nr, ringzahl, teiler, gueltigkeit = shot

            ttk.Label(frame, text=f"{schuss_nr}").grid(row=i+1, column=0, padx=5, pady=5)

            ring_var = tk.StringVar(value=str(ringzahl))
            teiler_var = tk.StringVar(value=str(teiler))

            e_ring = ttk.Entry(frame, textvariable=ring_var, width=10)
            e_ring.grid(row=i+1, column=1, padx=5, pady=5)

            e_teiler = ttk.Entry(frame, textvariable=teiler_var, width=10)
            e_teiler.grid(row=i+1, column=2, padx=5, pady=5)

            self.entries.append({
                "id": shot_id,
                "schuss_nr": schuss_nr,
                "orig_ring": ringzahl,
                "orig_teiler": teiler,
                "ring_var": ring_var,
                "teiler_var": teiler_var
            })

        btn_frame = ttk.Frame(self)
        btn_frame.pack(fill="x", pady=10)

        ttk.Button(btn_frame, text="Änderung senden", command=self.send_changes).pack(side="left", padx=20)
        ttk.Button(btn_frame, text="Abbrechen", command=self.destroy).pack(side="right", padx=20)

    def send_changes(self):
        edi_cmd = f"EDI={self.total_shots};{len(self.shots)}"
        self.serial_manager.send_prot(edi_cmd)

        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()

        # Build a map of edited shots
        edited_shots = {}
        for entry in self.entries:
            try:
                new_ring = float(entry["ring_var"].get().replace(',', '.'))
                new_teiler = float(entry["teiler_var"].get().replace(',', '.'))
            except ValueError:
                # Fallback to original if invalid input
                new_ring = entry["orig_ring"]
                new_teiler = entry["orig_teiler"]

            is_changed = (new_ring != entry["orig_ring"]) or (new_teiler != entry["orig_teiler"])
            flag = "V" if is_changed else "U"

            edited_shots[entry["id"]] = {
                "new_ring": new_ring,
                "new_teiler": new_teiler,
                "flag": flag,
                "schuss_nr": entry["schuss_nr"]
            }

        if self.is_shootcup:
            c.execute('''
                SELECT id, schuss_nr, ringzahl, teiler
                FROM Shootcup_Ergebnisse
                ORDER BY schuss_nr ASC
            ''')
        else:
            # Fetch ALL shots for this shooter
            c.execute('''
                SELECT id, schuss_nr, ringzahl, teiler
                FROM Ergebnisse
                WHERE turnier_schuetze_klasse_id=?
                ORDER BY schuss_nr ASC
            ''', (self.entry_id,))
        all_shots = c.fetchall()

        for shot in all_shots:
            shot_id, schuss_nr, ringzahl, teiler = shot

            if shot_id in edited_shots:
                # It's one of the shots from the last target that could be edited
                edit_data = edited_shots[shot_id]
                s_cmd = f"S={schuss_nr};{edit_data['new_ring']};{edit_data['new_teiler']};{edit_data['flag']}"
                self.serial_manager.send_prot(s_cmd)

                # Update DB
                if self.is_shootcup:
                    c.execute('''
                        UPDATE Shootcup_Ergebnisse
                        SET ringzahl=?, teiler=?, gueltigkeit='Überprüft'
                        WHERE id=?
                    ''', (edit_data['new_ring'], edit_data['new_teiler'], shot_id))
                else:
                    c.execute('''
                        UPDATE Ergebnisse
                        SET ringzahl=?, teiler=?, gueltigkeit='Überprüft'
                        WHERE id=?
                    ''', (edit_data['new_ring'], edit_data['new_teiler'], shot_id))
            else:
                # It's an older shot (not part of the current target/kontrolle)
                s_cmd = f"S={schuss_nr};{ringzahl};{teiler};U"
                self.serial_manager.send_prot(s_cmd)

        conn.commit()
        conn.close()

        self.callback()
        self.destroy()
