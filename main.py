import tkinter as tk
from tkinter import ttk
import sqlite3

from db_manager import DB_PATH, init_db
from serial_manager import SerialManager
from ui_klassen import KlassenUI
from ui_schuetzen import SchuetzenUI
from ui_turniere import TurniereUI
from ui_auswertung import AuswertungUI
from ui_auswertung_shootcup import AuswertungShootcupUI
from ui_verbindung import VerbindungUI
from ui_legacy import LegacyUI

class DisagRM3App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("DISAG RM III - Turniermanager")
        self.geometry("1300x900")
        
        # Initialize DB if missing
        init_db()
        
        # Initialize Serial Manager (Shared between Tab 4 and Tab 5)
        self.serial_manager = SerialManager(DB_PATH)

        # Setup Notebook (Tabs)
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill='both', expand=True, padx=5, pady=5)

        # Create Tabs
        self.tab_klassen = KlassenUI(self.notebook, DB_PATH)
        self.tab_schuetzen = SchuetzenUI(self.notebook, DB_PATH)
        self.tab_turniere = TurniereUI(self.notebook, DB_PATH)
        self.tab_auswertung = AuswertungUI(self.notebook, DB_PATH, self.serial_manager)
        self.tab_auswertung_shootcup = AuswertungShootcupUI(self.notebook, DB_PATH, self.serial_manager)
        self.tab_verbindung = VerbindungUI(self.notebook, self.serial_manager)
        self.tab_legacy = LegacyUI(self.notebook)

        self.notebook.add(self.tab_klassen, text="Klassenverwaltung")
        self.notebook.add(self.tab_schuetzen, text="Schützenverwaltung")
        self.notebook.add(self.tab_turniere, text="Turnierverwaltung")
        self.notebook.add(self.tab_auswertung, text="Auswertung")
        self.notebook.add(self.tab_auswertung_shootcup, text="Auswertung Shootcup")
        self.notebook.add(self.tab_verbindung, text="Verbindung")
        self.notebook.add(self.tab_legacy, text="Verbindungstest")

    def destroy(self):
        # Cleanup serial on exit
        if self.serial_manager.is_connected():
            self.serial_manager.disconnect()
        # Cleanup legacy serial if exists
        if self.tab_legacy.ser and self.tab_legacy.ser.is_open:
            self.tab_legacy.running = False
            self.tab_legacy.ser.close()
        super().destroy()

if __name__ == "__main__":
    app = DisagRM3App()
    app.mainloop()
