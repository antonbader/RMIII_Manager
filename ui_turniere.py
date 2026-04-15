import tkinter as tk
from tkinter import ttk, messagebox
import sqlite3

class TurniereUI(ttk.Frame):
    def __init__(self, parent, db_path):
        super().__init__(parent)
        self.db_path = db_path


        # Split into Top (Turniere) and Bottom (Klassen/Schützen Zuordnung)
        self.paned = ttk.PanedWindow(self, orient=tk.VERTICAL)
        self.paned.pack(fill="both", expand=True)

        # TOP FRAME
        self.top_frame = ttk.Frame(self.paned)
        self.paned.add(self.top_frame, weight=1)

        form_frame = ttk.LabelFrame(self.top_frame, text="Neues / Bearbeitetes Turnier", padding=10)
        form_frame.pack(fill="x", pady=5)

        ttk.Label(form_frame, text="Turniername:").grid(row=0, column=0, sticky="e", padx=5)
        self.name_var = tk.StringVar()
        ttk.Entry(form_frame, textvariable=self.name_var, width=30).grid(row=0, column=1, sticky="w", padx=5)

        ttk.Label(form_frame, text="Datum/Zeitraum:").grid(row=1, column=0, sticky="e", padx=5, pady=5)
        self.zeit_var = tk.StringVar()
        ttk.Entry(form_frame, textvariable=self.zeit_var, width=30).grid(row=1, column=1, sticky="w", padx=5, pady=5)

        btn_frame = ttk.Frame(form_frame)
        btn_frame.grid(row=2, column=0, columnspan=2, pady=10)
        ttk.Button(btn_frame, text="Speichern", command=self.save_turnier).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Abbrechen", command=self.clear_form).pack(side="left", padx=5)

        table_top_frame = ttk.Frame(self.top_frame)
        table_top_frame.pack(fill="x", pady=5)
        ttk.Label(table_top_frame, text="Suchen:").pack(side="left", padx=5)
        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", lambda *args: self.load_turniere())
        ttk.Entry(table_top_frame, textvariable=self.search_var).pack(side="left", fill="x", expand=True, padx=5)

        self.tree = ttk.Treeview(self.top_frame, columns=("ID", "Name", "Zeitraum"), show="headings", selectmode="browse")
        self.tree.heading("ID", text="ID", command=lambda: self.sort_column(self.tree, "ID", False))
        self.tree.heading("Name", text="Turniername", command=lambda: self.sort_column(self.tree, "Name", False))
        self.tree.heading("Zeitraum", text="Zeitraum", command=lambda: self.sort_column(self.tree, "Zeitraum", False))
        self.tree.column("ID", width=50, stretch=False)
        self.tree.pack(fill="both", expand=True, pady=5)
        self.tree.bind("<<TreeviewSelect>>", self.on_turnier_select)

        action_frame = ttk.Frame(self.top_frame)
        action_frame.pack(fill="x", pady=5)
        ttk.Button(action_frame, text="Löschen", command=self.delete_turnier).pack(side="right", padx=5)
        ttk.Button(action_frame, text="Bearbeiten", command=self.edit_turnier).pack(side="right", padx=5)

        self.editing_id = None

        # BOTTOM FRAME
        self.bottom_frame = ttk.LabelFrame(self.paned, text="Turnier-Details (Bitte Turnier auswählen)", padding=10)
        self.paned.add(self.bottom_frame, weight=2)

        # Grid config to let the lists expand but keep the bottom buttons visible
        self.bottom_frame.rowconfigure(0, weight=1)
        self.bottom_frame.columnconfigure(0, weight=1)

        self.setup_bottom_frame()

        self.load_turniere()

    def get_db_connection(self):
        return sqlite3.connect(self.db_path)

    # --- TOP FRAME LOGIC ---
    def load_turniere(self):
        for item in self.tree.get_children():
            self.tree.delete(item)

        search_term = f"%{self.search_var.get()}%"
        conn = self.get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, name, zeitraum FROM Turniere WHERE name LIKE ? OR zeitraum LIKE ?", (search_term, search_term))
        for row in cursor.fetchall():
            self.tree.insert("", "end", values=row)
        conn.close()

    def save_turnier(self):
        name = self.name_var.get().strip()
        zeit = self.zeit_var.get().strip()
        if not name:
            messagebox.showerror("Fehler", "Turniername ist ein Pflichtfeld!")
            return

        conn = self.get_db_connection()
        cursor = conn.cursor()
        if self.editing_id:
            cursor.execute("UPDATE Turniere SET name=?, zeitraum=? WHERE id=?", (name, zeit, self.editing_id))
        else:
            cursor.execute("INSERT INTO Turniere (name, zeitraum) VALUES (?, ?)", (name, zeit))
        conn.commit()
        conn.close()
        self.clear_form()
        self.load_turniere()

    def clear_form(self):
        self.name_var.set("")
        self.zeit_var.set("")
        self.editing_id = None
        self.tree.selection_remove(self.tree.selection())

    def edit_turnier(self):
        selected = self.tree.selection()
        if not selected: return
        item = self.tree.item(selected[0])
        values = item['values']
        self.editing_id = values[0]
        self.name_var.set(values[1])
        self.zeit_var.set(values[2] if values[2] != "None" else "")

    def delete_turnier(self):
        selected = self.tree.selection()
        if not selected: return
        if messagebox.askyesno("Löschen", "Turnier und alle zugehörigen Daten (Schützen, Ergebnisse) löschen?"):
            t_id = self.tree.item(selected[0])['values'][0]
            conn = self.get_db_connection()
            cursor = conn.cursor()
            # Cascade delete manually since foreign keys might not have ON DELETE CASCADE
            cursor.execute("DELETE FROM Ergebnisse WHERE turnier_schuetze_klasse_id IN (SELECT id FROM Turnier_Schuetzen_Klassen WHERE turnier_id=?)", (t_id,))
            cursor.execute("DELETE FROM Turnier_Schuetzen_Klassen WHERE turnier_id=?", (t_id,))
            cursor.execute("DELETE FROM Turnier_Klassen WHERE turnier_id=?", (t_id,))
            cursor.execute("DELETE FROM Turniere WHERE id=?", (t_id,))
            conn.commit()
            conn.close()
            self.load_turniere()
            self.clear_bottom_frame()

    def on_turnier_select(self, event):
        selected = self.tree.selection()
        if not selected:
            self.clear_bottom_frame()
            return
        t_id = self.tree.item(selected[0])['values'][0]
        t_name = self.tree.item(selected[0])['values'][1]
        self.bottom_frame.config(text=f"Turnier-Details: {t_name}")
        self.load_klassen_lists(t_id)

    def sort_column(self, tree, col, reverse):
        l = [(tree.set(k, col), k) for k in tree.get_children('')]
        try: l.sort(key=lambda t: float(t[0]), reverse=reverse)
        except ValueError: l.sort(reverse=reverse)
        for index, (val, k) in enumerate(l): tree.move(k, '', index)
        tree.heading(col, command=lambda: self.sort_column(tree, col, not reverse))

    # --- BOTTOM FRAME LOGIC ---
    def setup_bottom_frame(self):
        # Two lists for Classes
        klassen_frame = ttk.Frame(self.bottom_frame)
        klassen_frame.grid(row=0, column=0, sticky="nsew", pady=5)

        # Left: Available Classes
        left_frame = ttk.Frame(klassen_frame)
        left_frame.pack(side="left", fill="both", expand=True)
        ttk.Label(left_frame, text="Verfügbare Klassen").pack()
        self.tree_avail = ttk.Treeview(left_frame, columns=("ID", "Name"), show="headings")
        self.tree_avail.heading("Name", text="Name")
        self.tree_avail.column("ID", width=0, stretch=False)
        self.tree_avail.pack(fill="both", expand=True)

        # Middle: Buttons
        mid_frame = ttk.Frame(klassen_frame)
        mid_frame.pack(side="left", padx=10)
        ttk.Button(mid_frame, text=">>", command=self.add_klasse_to_turnier).pack(pady=5)
        ttk.Button(mid_frame, text="<<", command=self.remove_klasse_from_turnier).pack(pady=5)

        # Right: Assigned Classes
        right_frame = ttk.Frame(klassen_frame)
        right_frame.pack(side="left", fill="both", expand=True)
        ttk.Label(right_frame, text="Zugewiesene Klassen").pack()
        self.tree_assigned = ttk.Treeview(right_frame, columns=("ID", "Name"), show="headings")
        self.tree_assigned.heading("Name", text="Name (* = nicht bearbeitet)")
        self.tree_assigned.column("ID", width=0, stretch=False)
        self.tree_assigned.pack(fill="both", expand=True)

        # Bottom Buttons
        btn_frame = ttk.Frame(self.bottom_frame)
        btn_frame.grid(row=1, column=0, sticky="ew", pady=5)
        ttk.Button(btn_frame, text="Klassen-Einstellungen bearbeiten", command=self.open_settings).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Schützen hinzufügen", command=self.open_schuetzen_window).pack(side="right", padx=5)

    def clear_bottom_frame(self):
        self.bottom_frame.config(text="Turnier-Details (Bitte Turnier auswählen)")
        for item in self.tree_avail.get_children(): self.tree_avail.delete(item)
        for item in self.tree_assigned.get_children(): self.tree_assigned.delete(item)

    def load_klassen_lists(self, t_id):
        for item in self.tree_avail.get_children(): self.tree_avail.delete(item)
        for item in self.tree_assigned.get_children(): self.tree_assigned.delete(item)

        conn = self.get_db_connection()
        cursor = conn.cursor()

        # Assigned classes
        cursor.execute('''
            SELECT k.id, k.name, tk.edited
            FROM Klassen k
            JOIN Turnier_Klassen tk ON k.id = tk.klasse_id
            WHERE tk.turnier_id = ?
        ''', (t_id,))
        assigned = cursor.fetchall()
        assigned_ids = []
        for row in assigned:
            k_id, k_name, edited = row
            display_name = k_name if edited else f"{k_name}*"
            self.tree_assigned.insert("", "end", values=(k_id, display_name))
            assigned_ids.append(k_id)

        # Available classes
        cursor.execute("SELECT id, name FROM Klassen")
        all_classes = cursor.fetchall()
        for row in all_classes:
            if row[0] not in assigned_ids:
                self.tree_avail.insert("", "end", values=row)

        conn.close()

    def get_selected_turnier_id(self):
        selected = self.tree.selection()
        if not selected: return None
        return self.tree.item(selected[0])['values'][0]

    def add_klasse_to_turnier(self):
        t_id = self.get_selected_turnier_id()
        if not t_id: return
        selected = self.tree_avail.selection()
        if not selected: return

        conn = self.get_db_connection()
        cursor = conn.cursor()
        for item in selected:
            k_id = self.tree_avail.item(item)['values'][0]
            cursor.execute("INSERT INTO Turnier_Klassen (turnier_id, klasse_id) VALUES (?, ?)", (t_id, k_id))
        conn.commit()
        conn.close()
        self.load_klassen_lists(t_id)

    def remove_klasse_from_turnier(self):
        t_id = self.get_selected_turnier_id()
        if not t_id: return
        selected = self.tree_assigned.selection()
        if not selected: return

        conn = self.get_db_connection()
        cursor = conn.cursor()
        for item in selected:
            k_id = self.tree_assigned.item(item)['values'][0]
            # Optionally warn if shooters are already assigned
            cursor.execute("DELETE FROM Turnier_Klassen WHERE turnier_id=? AND klasse_id=?", (t_id, k_id))
            cursor.execute("DELETE FROM Turnier_Schuetzen_Klassen WHERE turnier_id=? AND klasse_id=?", (t_id, k_id))
        conn.commit()
        conn.close()
        self.load_klassen_lists(t_id)

    def open_settings(self):
        t_id = self.get_selected_turnier_id()
        if not t_id: return
        selected = self.tree_assigned.selection()
        if not selected:
            messagebox.showinfo("Info", "Bitte eine zugewiesene Klasse auswählen.")
            return

        k_id = self.tree_assigned.item(selected[0])['values'][0]
        k_name = self.tree_assigned.item(selected[0])['values'][1].replace('*', '')

        SettingsWindow(self, self.db_path, t_id, k_id, k_name, lambda: self.load_klassen_lists(t_id))

    def open_schuetzen_window(self):
        t_id = self.get_selected_turnier_id()
        if not t_id:
            messagebox.showinfo("Info", "Bitte ein Turnier auswählen.")
            return

        # Get tournament name
        selected = self.tree.selection()
        t_name = self.tree.item(selected[0])['values'][1]

        SchuetzenAddWindow(self, self.db_path, t_id, t_name)

class SettingsWindow(tk.Toplevel):
    def __init__(self, parent, db_path, t_id, k_id, k_name, callback):
        super().__init__(parent)
        self.db_path = db_path
        self.t_id = t_id
        self.k_id = k_id
        self.callback = callback

        self.title(f"Einstellungen: {k_name}")
        self.geometry("400x300")
        self.grab_set()

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT sch, ria, tea, teg, ssc, sge FROM Turnier_Klassen WHERE turnier_id=? AND klasse_id=?", (t_id, k_id))
        row = cursor.fetchone()
        conn.close()

        if not row:
            self.destroy()
            return

        sch, ria, tea, teg, ssc, sge = row

        ttk.Label(self, text="Scheibentype (SCH):").grid(row=0, column=0, sticky="w", padx=10, pady=5)
        self.cb_sch = ttk.Combobox(self, values=["LG10", "LG5", "LGES", "LP"])
        self.cb_sch.set(sch)
        self.cb_sch.grid(row=0, column=1, padx=10, pady=5)

        ttk.Label(self, text="Ringauswertung (RIA):").grid(row=1, column=0, sticky="w", padx=10, pady=5)
        self.cb_ria = ttk.Combobox(self, values=["GR", "ZR", "KR"])
        self.cb_ria.set(ria)
        self.cb_ria.grid(row=1, column=1, padx=10, pady=5)

        ttk.Label(self, text="Teilerauswertung (TEA):").grid(row=2, column=0, sticky="w", padx=10, pady=5)
        self.cb_tea = ttk.Combobox(self, values=["KT", "ZT"])
        self.cb_tea.set(tea)
        self.cb_tea.grid(row=2, column=1, padx=10, pady=5)

        ttk.Label(self, text="Teilergrenze (TEG):").grid(row=3, column=0, sticky="w", padx=10, pady=5)
        self.sb_teg = ttk.Spinbox(self, from_=100, to=4000)
        self.sb_teg.set(teg)
        self.sb_teg.grid(row=3, column=1, padx=10, pady=5)

        ttk.Label(self, text="Schusszahl/Scheibe (SSC):").grid(row=4, column=0, sticky="w", padx=10, pady=5)
        self.sb_ssc = ttk.Spinbox(self, from_=1, to=10)
        self.sb_ssc.set(ssc)
        self.sb_ssc.grid(row=4, column=1, padx=10, pady=5)

        ttk.Label(self, text="Schusszahl Gesamt (SGE):").grid(row=5, column=0, sticky="w", padx=10, pady=5)
        self.sb_sge = ttk.Spinbox(self, from_=1, to=120)
        self.sb_sge.set(sge)
        self.sb_sge.grid(row=5, column=1, padx=10, pady=5)

        ttk.Button(self, text="Speichern", command=self.save).grid(row=6, column=0, columnspan=2, pady=15)

    def save(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE Turnier_Klassen
            SET sch=?, ria=?, tea=?, teg=?, ssc=?, sge=?, edited=1
            WHERE turnier_id=? AND klasse_id=?
        ''', (self.cb_sch.get(), self.cb_ria.get(), self.cb_tea.get(), self.sb_teg.get(), self.sb_ssc.get(), self.sb_sge.get(), self.t_id, self.k_id))
        conn.commit()
        conn.close()
        self.callback()
        self.destroy()

class SchuetzenAddWindow(tk.Toplevel):
    def __init__(self, parent, db_path, t_id, t_name):
        super().__init__(parent)
        self.db_path = db_path
        self.t_id = t_id

        self.title(f"Schützen zu Turnier '{t_name}' hinzufügen")
        self.geometry("900x600")
        self.grab_set()

        # TOP FRAME for Lists
        top_frame = ttk.Frame(self)
        top_frame.pack(fill="both", expand=True, padx=10, pady=10)

        # Left: Shooters
        left_f = ttk.Frame(top_frame)
        left_f.pack(side="left", fill="both", expand=True, padx=5)
        ttk.Label(left_f, text="Schützen").pack()

        self.s_search_var = tk.StringVar()
        self.s_search_var.trace_add("write", lambda *args: self.load_schuetzen())
        ttk.Entry(left_f, textvariable=self.s_search_var).pack(fill="x")

        self.tree_s = ttk.Treeview(left_f, columns=("ID", "Name"), show="headings", selectmode="browse")
        self.tree_s.heading("Name", text="Name", command=lambda: self.sort_column(self.tree_s, "Name", False))
        self.tree_s.column("ID", width=0, stretch=False)
        self.tree_s.pack(fill="both", expand=True)

        # Middle: Classes assigned to tournament
        mid_f = ttk.Frame(top_frame)
        mid_f.pack(side="left", fill="both", expand=True, padx=5)
        ttk.Label(mid_f, text="Klassen").pack()

        self.k_search_var = tk.StringVar()
        self.k_search_var.trace_add("write", lambda *args: self.load_klassen())
        ttk.Entry(mid_f, textvariable=self.k_search_var).pack(fill="x")

        # Extended select mode to select multiple classes
        self.tree_k = ttk.Treeview(mid_f, columns=("ID", "Name"), show="headings", selectmode="extended")
        self.tree_k.heading("Name", text="Klassen", command=lambda: self.sort_column(self.tree_k, "Name", False))
        self.tree_k.column("ID", width=0, stretch=False)
        self.tree_k.pack(fill="both", expand=True)

        # Action Buttons
        ttk.Button(top_frame, text="Speichern (⬇)", command=self.add_mapping).pack(side="left", padx=5)

        # BOTTOM FRAME for existing entries
        bot_frame = ttk.Frame(self)
        bot_frame.pack(fill="both", expand=True, padx=10, pady=10)

        ttk.Label(bot_frame, text="Gespeicherte Einträge für dieses Turnier").pack(anchor="w")

        self.e_search_var = tk.StringVar()
        self.e_search_var.trace_add("write", lambda *args: self.load_entries())
        s_frame = ttk.Frame(bot_frame)
        s_frame.pack(fill="x")
        ttk.Label(s_frame, text="Suchen:").pack(side="left")
        ttk.Entry(s_frame, textvariable=self.e_search_var).pack(side="left", fill="x", expand=True)

        self.tree_e = ttk.Treeview(bot_frame, columns=("ID", "Schütze", "Klasse"), show="headings")
        self.tree_e.heading("Schütze", text="Schütze", command=lambda: self.sort_column(self.tree_e, "Schütze", False))
        self.tree_e.heading("Klasse", text="Klasse", command=lambda: self.sort_column(self.tree_e, "Klasse", False))
        self.tree_e.column("ID", width=0, stretch=False)
        self.tree_e.pack(fill="both", expand=True, pady=5)

        ttk.Button(bot_frame, text="Eintrag löschen", command=self.delete_mapping).pack(anchor="e")

        self.load_schuetzen()
        self.load_klassen()
        self.load_entries()

    def get_db_connection(self):
        return sqlite3.connect(self.db_path)

    def load_schuetzen(self):
        for i in self.tree_s.get_children(): self.tree_s.delete(i)
        st = f"%{self.s_search_var.get()}%"
        conn = self.get_db_connection()
        c = conn.cursor()
        c.execute("SELECT id, name FROM Schuetzen WHERE name LIKE ?", (st,))
        for row in c.fetchall(): self.tree_s.insert("", "end", values=row)
        conn.close()

    def load_klassen(self):
        for i in self.tree_k.get_children(): self.tree_k.delete(i)
        st = f"%{self.k_search_var.get()}%"
        conn = self.get_db_connection()
        c = conn.cursor()
        c.execute('''
            SELECT k.id, k.name
            FROM Klassen k
            JOIN Turnier_Klassen tk ON k.id = tk.klasse_id
            WHERE tk.turnier_id = ? AND k.name LIKE ?
        ''', (self.t_id, st))
        for row in c.fetchall(): self.tree_k.insert("", "end", values=row)
        conn.close()

    def load_entries(self):
        for i in self.tree_e.get_children(): self.tree_e.delete(i)
        st = f"%{self.e_search_var.get()}%"
        conn = self.get_db_connection()
        c = conn.cursor()
        c.execute('''
            SELECT tsk.id, s.name, k.name
            FROM Turnier_Schuetzen_Klassen tsk
            JOIN Schuetzen s ON tsk.schuetze_id = s.id
            JOIN Klassen k ON tsk.klasse_id = k.id
            WHERE tsk.turnier_id = ? AND (s.name LIKE ? OR k.name LIKE ?)
        ''', (self.t_id, st, st))
        for row in c.fetchall(): self.tree_e.insert("", "end", values=row)
        conn.close()

    def add_mapping(self):
        sel_s = self.tree_s.selection()
        sel_k = self.tree_k.selection()

        if not sel_s or not sel_k:
            messagebox.showinfo("Info", "Bitte einen Schützen und mindestens eine Klasse auswählen.")
            return

        s_id = self.tree_s.item(sel_s[0])['values'][0]

        conn = self.get_db_connection()
        c = conn.cursor()
        for k_item in sel_k:
            k_id = self.tree_k.item(k_item)['values'][0]
            # Check if exists
            c.execute("SELECT id FROM Turnier_Schuetzen_Klassen WHERE turnier_id=? AND schuetze_id=? AND klasse_id=?", (self.t_id, s_id, k_id))
            if not c.fetchone():
                c.execute("INSERT INTO Turnier_Schuetzen_Klassen (turnier_id, schuetze_id, klasse_id) VALUES (?, ?, ?)", (self.t_id, s_id, k_id))
        conn.commit()
        conn.close()
        self.load_entries()

    def sort_column(self, tree, col, reverse):
        l = [(tree.set(k, col), k) for k in tree.get_children('')]
        try: l.sort(key=lambda t: float(t[0]), reverse=reverse)
        except ValueError: l.sort(reverse=reverse)
        for index, (val, k) in enumerate(l): tree.move(k, '', index)
        tree.heading(col, command=lambda: self.sort_column(tree, col, not reverse))

    def delete_mapping(self):
        sel_e = self.tree_e.selection()
        if not sel_e: return

        conn = self.get_db_connection()
        c = conn.cursor()
        for item in sel_e:
            entry_id = self.tree_e.item(item)['values'][0]
            c.execute("DELETE FROM Ergebnisse WHERE turnier_schuetze_klasse_id=?", (entry_id,))
            c.execute("DELETE FROM Turnier_Schuetzen_Klassen WHERE id=?", (entry_id,))
        conn.commit()
        conn.close()
        self.load_entries()
