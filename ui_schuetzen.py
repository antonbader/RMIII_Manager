import tkinter as tk
from tkinter import ttk, messagebox
import sqlite3

class SchuetzenUI(ttk.Frame):
    def __init__(self, parent, db_path):
        super().__init__(parent)
        self.db_path = db_path
        self.pack(fill="both", expand=True, padx=10, pady=10)

        # Form
        form_frame = ttk.LabelFrame(self, text="Neuer / Bearbeiteter Schütze", padding=10)
        form_frame.pack(fill="x", pady=5)

        ttk.Label(form_frame, text="Name:").grid(row=0, column=0, sticky="e", padx=5)
        self.name_var = tk.StringVar()
        self.name_entry = ttk.Entry(form_frame, textvariable=self.name_var, width=30)
        self.name_entry.grid(row=0, column=1, sticky="w", padx=5)

        # Action Buttons
        btn_frame = ttk.Frame(form_frame)
        btn_frame.grid(row=1, column=0, columnspan=2, pady=10)

        self.btn_save = ttk.Button(btn_frame, text="Speichern", command=self.save_schuetze)
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
        self.tree = ttk.Treeview(self, columns=("ID", "Name"), show="headings", selectmode="browse")
        self.tree.heading("ID", text="ID", command=lambda: self.sort_column("ID", False))
        self.tree.heading("Name", text="Name", command=lambda: self.sort_column("Name", False))

        self.tree.column("ID", width=50, stretch=False)
        self.tree.column("Name", stretch=True)

        self.tree.pack(fill="both", expand=True, pady=5)

        # Edit / Delete Buttons
        action_frame = ttk.Frame(self)
        action_frame.pack(fill="x", pady=5)

        ttk.Button(action_frame, text="Löschen", command=self.delete_schuetze).pack(side="right", padx=5)
        ttk.Button(action_frame, text="Bearbeiten", command=self.edit_schuetze).pack(side="right", padx=5)

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
        cursor.execute("SELECT id, name FROM Schuetzen WHERE name LIKE ?", (search_term,))
        for row in cursor.fetchall():
            self.tree.insert("", "end", values=row)
        conn.close()

    def save_schuetze(self):
        name = self.name_var.get().strip()

        if not name:
            messagebox.showerror("Fehler", "Der Name ist ein Pflichtfeld!")
            return

        conn = self.get_db_connection()
        cursor = conn.cursor()

        if self.editing_id:
            cursor.execute("UPDATE Schuetzen SET name=? WHERE id=?", (name, self.editing_id))
        else:
            cursor.execute("INSERT INTO Schuetzen (name) VALUES (?)", (name,))

        conn.commit()
        conn.close()
        self.clear_form()
        self.load_data()

    def clear_form(self):
        self.name_var.set("")
        self.editing_id = None
        self.tree.selection_remove(self.tree.selection())

    def edit_schuetze(self):
        selected = self.tree.selection()
        if not selected:
            return
        item = self.tree.item(selected[0])
        values = item['values']
        self.editing_id = values[0]
        self.name_var.set(values[1])

    def delete_schuetze(self):
        selected = self.tree.selection()
        if not selected:
            return
        if messagebox.askyesno("Löschen", "Soll dieser Schütze wirklich gelöscht werden?"):
            item = self.tree.item(selected[0])
            s_id = item['values'][0]
            conn = self.get_db_connection()
            cursor = conn.cursor()
            cursor.execute("DELETE FROM Schuetzen WHERE id=?", (s_id,))
            conn.commit()
            conn.close()
            self.load_data()

    def sort_column(self, col, reverse):
        l = [(self.tree.set(k, col), k) for k in self.tree.get_children('')]
        try:
            l.sort(key=lambda t: float(t[0]), reverse=reverse)
        except ValueError:
            l.sort(reverse=reverse)

        for index, (val, k) in enumerate(l):
            self.tree.move(k, '', index)

        self.tree.heading(col, command=lambda: self.sort_column(col, not reverse))
