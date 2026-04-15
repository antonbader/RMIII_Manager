import tkinter as tk
from tkinter import ttk, messagebox
import sqlite3

class KlassenUI(ttk.Frame):
    def __init__(self, parent, db_path):
        super().__init__(parent)
        self.db_path = db_path


        # Form
        form_frame = ttk.LabelFrame(self, text="Neue / Bearbeitete Klasse", padding=10)
        form_frame.pack(fill="x", pady=5)

        ttk.Label(form_frame, text="Klassenname:").grid(row=0, column=0, sticky="e", padx=5)
        self.name_var = tk.StringVar()
        self.name_entry = ttk.Entry(form_frame, textvariable=self.name_var, width=30)
        self.name_entry.grid(row=0, column=1, sticky="w", padx=5)

        ttk.Label(form_frame, text="Beschreibung:").grid(row=1, column=0, sticky="e", padx=5, pady=5)
        self.desc_var = tk.StringVar()
        self.desc_entry = ttk.Entry(form_frame, textvariable=self.desc_var, width=50)
        self.desc_entry.grid(row=1, column=1, sticky="w", padx=5, pady=5)

        # Action Buttons
        btn_frame = ttk.Frame(form_frame)
        btn_frame.grid(row=2, column=0, columnspan=2, pady=10)

        self.btn_save = ttk.Button(btn_frame, text="Speichern", command=self.save_klasse)
        self.btn_save.pack(side="left", padx=5)

        self.btn_clear = ttk.Button(btn_frame, text="Abbrechen", command=self.clear_form)
        self.btn_clear.pack(side="left", padx=5)

        # Top Table Frame
        table_top_frame = ttk.Frame(self)
        table_top_frame.pack(fill="x", pady=5)

        ttk.Label(table_top_frame, text="Suchen:").pack(side="left", padx=5)
        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", lambda *args: self.load_data())
        ttk.Entry(table_top_frame, textvariable=self.search_var).pack(side="left", fill="x", expand=True, padx=5)

        # Table
        self.tree = ttk.Treeview(self, columns=("ID", "Name", "Beschreibung"), show="headings", selectmode="browse")
        self.tree.heading("ID", text="ID", command=lambda: self.sort_column("ID", False))
        self.tree.heading("Name", text="Klassenname", command=lambda: self.sort_column("Name", False))
        self.tree.heading("Beschreibung", text="Beschreibung", command=lambda: self.sort_column("Beschreibung", False))

        self.tree.column("ID", width=50, stretch=False)
        self.tree.column("Name", width=200, stretch=False)
        self.tree.column("Beschreibung", stretch=True)

        self.tree.pack(fill="both", expand=True, pady=5)
        self.tree.bind("<<TreeviewSelect>>", self.on_select)

        # Edit / Delete Buttons
        action_frame = ttk.Frame(self)
        action_frame.pack(fill="x", pady=5)

        ttk.Button(action_frame, text="Löschen", command=self.delete_klasse).pack(side="right", padx=5)
        ttk.Button(action_frame, text="Bearbeiten", command=self.edit_klasse).pack(side="right", padx=5)

        self.editing_id = None
        self.load_data()

    def get_db_connection(self):
        return sqlite3.connect(self.db_path)

    def load_data(self):
        for item in self.tree.get_children():
            self.tree.delete(item)

        search_term = f"%{self.search_var.get()}%"
        conn = self.get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, name, beschreibung FROM Klassen WHERE name LIKE ? OR beschreibung LIKE ?", (search_term, search_term))
        for row in cursor.fetchall():
            self.tree.insert("", "end", values=row)
        conn.close()

    def save_klasse(self):
        name = self.name_var.get().strip()
        desc = self.desc_var.get().strip()

        if not name:
            messagebox.showerror("Fehler", "Der Klassenname ist ein Pflichtfeld!")
            return

        conn = self.get_db_connection()
        cursor = conn.cursor()

        if self.editing_id:
            cursor.execute("UPDATE Klassen SET name=?, beschreibung=? WHERE id=?", (name, desc, self.editing_id))
        else:
            cursor.execute("INSERT INTO Klassen (name, beschreibung) VALUES (?, ?)", (name, desc))

        conn.commit()
        conn.close()
        self.clear_form()
        self.load_data()

    def clear_form(self):
        self.name_var.set("")
        self.desc_var.set("")
        self.editing_id = None
        self.tree.selection_remove(self.tree.selection())

    def on_select(self, event):
        pass # Optional: can auto-fill form, but we have an Edit button

    def edit_klasse(self):
        selected = self.tree.selection()
        if not selected:
            return
        item = self.tree.item(selected[0])
        values = item['values']
        self.editing_id = values[0]
        self.name_var.set(values[1])
        self.desc_var.set(values[2] if values[2] != "None" else "")

    def delete_klasse(self):
        selected = self.tree.selection()
        if not selected:
            return
        if messagebox.askyesno("Löschen", "Soll diese Klasse wirklich gelöscht werden?"):
            item = self.tree.item(selected[0])
            k_id = item['values'][0]
            conn = self.get_db_connection()
            cursor = conn.cursor()
            cursor.execute("DELETE FROM Klassen WHERE id=?", (k_id,))
            conn.commit()
            conn.close()
            self.load_data()

    def sort_column(self, col, reverse):
        l = [(self.tree.set(k, col), k) for k in self.tree.get_children('')]
        try:
            # Try sorting numerically if possible (e.g., ID)
            l.sort(key=lambda t: float(t[0]), reverse=reverse)
        except ValueError:
            # Otherwise, sort alphabetically
            l.sort(reverse=reverse)

        for index, (val, k) in enumerate(l):
            self.tree.move(k, '', index)

        self.tree.heading(col, command=lambda: self.sort_column(col, not reverse))
