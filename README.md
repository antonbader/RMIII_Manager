# DISAG RM III - Turniermanager

Ein in Python geschriebener Desktop-Turniermanager zur Anbindung an das DISAG RM III Auswertegerät. Diese Software ermöglicht die Verwaltung von Schützen, Klassen und Turnieren sowie die direkte Übernahme von Schießergebnissen über die serielle Schnittstelle.

Zudem bietet die Anwendung eine direkte Anbindung an [Shootcup](https://github.com/antonbader/shootcup), um geschossene Ergebnisse automatisiert über eine REST-API weiterzuleiten.

## Features

- **Schützen- & Klassenverwaltung:** Einfaches Anlegen und Verwalten von Teilnehmern und Alters-/Wettkampfklassen.
- **Turnierverwaltung:** Erstellung von Turnieren mit Zuweisung von Schützen zu spezifischen Klassen.
- **Auswertung & Verbindung:** Empfang von Schussergebnissen direkt vom DISAG RM III Gerät (Ringzahl, Teiler, Winkel, Gültigkeit).
- **Shootcup-Integration:** Dedizierter Auswertungsmodus, der geschossene Ergebnisse direkt an die Shootcup-API sendet.
- **Excel-Export:** Möglichkeit, Ergebnisse in Excel-Dateien zu exportieren (mit deutscher Zahlenformatierung).

## Voraussetzungen

- Python 3.x
- Erforderliche Python-Pakete: `pyserial`, `pandas`, `openpyxl`, `reportlab`, `requests`
- Tkinter (meist bei Python vorinstalliert, bei Linux ggf. via Paketmanager nachinstallieren, z.B. `sudo apt-get install python3-tk`)

## Installation & Starten

1. Klone oder lade das Repository herunter.
2. Installiere die benötigten Abhängigkeiten:
   ```bash
   pip install pyserial pandas openpyxl reportlab requests
   ```
3. Führe die Hauptdatei aus, um die Applikation zu starten:
   ```bash
   python3 main.py
   ```
   *(Hinweis: Falls in einer Headless-Umgebung gearbeitet wird, kann xvfb-run -a python3 main.py verwendet werden).*

## Verbindungsaufbau zum DISAG RM III

**WICHTIG:** Für den korrekten Verbindungsaufbau mit dem DISAG RM III Gerät ist ein zweistufiger Prozess über die serielle Schnittstelle erforderlich:

1. **Initiale Verbindung:** Zuerst muss die Verbindung mit **2400 Baud** initialisiert werden (Gerät in Bereitschaft bringen).
2. **Betriebsverbindung:** Anschließend muss die Verbindung getrennt und direkt wieder mit **9600 Baud** aufgebaut werden, um in den eigentlichen Kommunikations- und Auswertungsmodus zu wechseln.

Dies kann in der Benutzeroberfläche unter dem Reiter "Verbindung" durchgeführt werden.

## Konfiguration (`config.json`)

Das Projekt nutzt eine `config.json` Datei im Hauptverzeichnis für benutzerdefinierte Einstellungen. Diese Datei sollte bei Bedarf manuell in einem Texteditor angepasst werden und wird nicht über die GUI konfiguriert.

Beispiel einer `config.json`:
```json
{
    "shootcup_api_url": "http://localhost:5003/api/score",
    "show_verbindungstest_tab": false
}
```

- `shootcup_api_url`: Die REST-API-URL der laufenden Shootcup-Instanz, an die die Ergebnisse gesendet werden sollen.
- `show_verbindungstest_tab`: Setzt man diesen Wert auf `true`, wird ein zusätzlicher Reiter "Verbindungstest" (Legacy UI) für Debugging-Zwecke eingeblendet.

## Schnittstelle zu Shootcup

Die Anwendung besitzt einen separaten Reiter "Auswertung Shootcup". In diesem Modus arbeitet der Turniermanager als Client für die [Shootcup-Software](https://github.com/antonbader/shootcup).
Anstatt die Ergebnisse nur in der lokalen SQLite-Datenbank abzulegen, werden neu empfangene Schüsse in Echtzeit im JSON-Format an die unter `shootcup_api_url` definierte Schnittstelle gesendet.

## Projektstruktur

- `main.py`: Einsprungspunkt der Applikation. Initialisiert das UI, die Datenbank und den SerialManager.
- `db_manager.py`: Kümmert sich um die Erstellung und Verbindung zur lokalen SQLite-Datenbank.
- `serial_manager.py`: Steuert die asynchrone Kommunikation (via `pyserial`) mit dem Auswertegerät sowie das Parsen des RM3-Protokolls.
- `ui_*.py` Dateien: Enthalten die Logik und Tkinter-Layouts für die jeweiligen Tabs (z.B. `ui_schuetzen.py`, `ui_turniere.py`, `ui_auswertung.py`).
- `config.json`: Konfigurationsdatei für API-URLs und UI-Feature-Toggles.
