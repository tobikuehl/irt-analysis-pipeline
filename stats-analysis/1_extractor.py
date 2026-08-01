import os
import re
import zipfile
import pandas as pd
from datetime import datetime

def extract_id_from_filename(filename):
    """Schneidet .odt ab und gibt den reinen Dateinamen als ID zurück."""
    name_without_ext = os.path.splitext(filename)[0]
    clean_id = re.sub(r'(_report|_Report|_bericht|-bericht).*$', '', name_without_ext, flags=re.IGNORECASE)
    return clean_id.strip("_ ")

def process_odt_xml(xml_content, filename):
    records = []

    # 1. XML-Tags durch Leerzeichen ersetzen und Text bereinigen
    clean_text = re.sub(r'<[^>]+>', ' ', xml_content)
    clean_text = re.sub(r'\s+', ' ', clean_text)

    subject_id = extract_id_from_filename(filename)

    # 2. Text an jeder 17-stelligen Foto-ID aufspalten
    sections = re.split(r'(?=\b\d{17}\b)', clean_text)

    key_mapping = {
        "Po1: Max": "temp_aoi_a_max",
        "Po1: Avg": "temp_aoi_a_avg",
        "Po2: Max": "temp_aoi_b_max",
        "Po2: Avg": "temp_aoi_b_avg"
    }

    meas_pattern = re.compile(r'(Po\d):\s*(Max|Avg)\.\s*Temp\.\s*([-\d.]+)\s*°C')
    # Sucht nach einer einzelnen Ziffer 0-4, die isoliert nach den Messergebnissen steht
    phase_pattern = re.compile(r'°C\s*\b([0-4])\b')

    for section in sections:
        time_match = re.match(r'^(\d{14})(\d{3})', section.strip())
        if not time_match:
            continue

        timestamp_str = time_match.group(1)
        try:
            current_dt = datetime.strptime(timestamp_str, "%Y%m%d%H%M%S")
        except ValueError:
            continue

        # Phase für diesen spezifischen Block extrahieren
        phase_match = phase_pattern.search(section)
        current_phase = int(phase_match.group(1)) if phase_match else None

        meas_matches = meas_pattern.findall(section)
        for po, typ, value in meas_matches:
            raw_key = f"{po}: {typ}"
            if raw_key in key_mapping:
                records.append({
                    "id": subject_id,
                    "timestamp_format": current_dt,
                    "time_phase_raw": current_phase, # Wird gleich in Wideform aufgefüllt
                    "variable": key_mapping[raw_key],
                    "value": float(value)
                })

    return records

def main():
    all_data = []
    files = [f for f in os.listdir('.') if f.endswith('.odt')]

    if not files:
        print("Keine .odt Dateien im Ordner gefunden!")
        return

    print(f"Verarbeite {len(files)} ODT-Dateien direkt via XML-Parsing...")

    for file in files:
        try:
            with zipfile.ZipFile(file) as z:
                xml_content = z.read('content.xml').decode('utf-8')
        except Exception as e:
            print(f"Fehler beim Lesen von {file}: {e}")
            continue

        file_records = process_odt_xml(xml_content, file)
        print(f" -> {file} (ID: {extract_id_from_filename(file)}): {int(len(file_records)/4)} Bilder gefunden.")
        all_data.extend(file_records)

    if not all_data:
        print("\n[Fehler] Es konnten keine Daten extrahiert werden.")
        return

    # DataFrame erstellen & Duplikate filtern
    df_long = pd.DataFrame(all_data)
    df_long.drop_duplicates(subset=["id", "timestamp_format", "variable"], inplace=True)

    # Pivotierung in die Wideform
    # Wir nehmen "time_phase_raw" mit in den Index auf, damit der Wert erhalten bleibt
    df_wide = df_long.pivot(
        index=["id", "timestamp_format", "time_phase_raw"],
        columns="variable",
        values="value"
    ).reset_index()

    # Chronologisch sortieren für das korrekte Auffüllen der Phasen
    df_wide.sort_values(by=["id", "timestamp_format"], inplace=True)

    # Vorwärts-Auffüllen (Forward Fill) der Phase innerhalb jeder ID [1]
    # Falls das allererste Bild keine Phase hat, wird mit 0 aufgefüllt
    df_wide["time_phase"] = df_wide.groupby("id")["time_phase_raw"].ffill().fillna(0).astype(int)

    # Weitere statistische Metriken berechnen
    df_wide["image_seq"] = df_wide.groupby("id").cumcount() + 1
    df_wide["time_seconds"] = df_wide.groupby("id")["timestamp_format"].transform(lambda x: (x - x.min()).dt.total_seconds().astype(int))
    df_wide["timestamp"] = df_wide["timestamp_format"].dt.strftime('%Y-%m-%d %H:%M:%S')

    # Zielstruktur exakt nach deinen Vorgaben anordnen
    target_cols = [
        "id", "image_seq", "timestamp", "time_seconds", "time_phase",
        "temp_aoi_a_max", "temp_aoi_a_avg", "temp_aoi_b_max", "temp_aoi_b_avg"
    ]

    df_final = df_wide[target_cols]

    # CSV Export
    output_file = "pilotstudie_lmm_wide.csv"
    df_final.to_csv(output_file, index=False, sep=";")
    print(f"\nErfolgreich beendet! Datei gespeichert unter: '{output_file}'")
    print(f"Gesamtzeilen in der CSV: {len(df_final)}")

if __name__ == "__main__":
    main()
