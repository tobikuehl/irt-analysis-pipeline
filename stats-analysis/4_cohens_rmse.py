import pandas as pd
import numpy as np

def brute_force_numeric(series):
    """Zwingt Text-Zahlen in Floats, egal wie kaputt das Format ist."""
    # Alles in String umwandeln, Anführungszeichen weg, Komma zu Punkt
    clean_series = series.astype(str).str.replace('"', '').str.replace(',', '.').str.strip()
    # Alles entfernen, was keine Zahl, Punkt oder Minuszeichen ist
    clean_series = clean_series.str.replace(r'[^0-9\.-]', '', regex=True)
    return pd.to_numeric(clean_series, errors='coerce')

try:
    # 1. DATEN LADEN (Wir nutzen hier Komma als Standard)
    df_summary = pd.read_csv('cohens_d.csv', sep=None, engine='python')
    df_ts = pd.read_csv('Messungen_zeitreihen.csv', sep=None, engine='python')

    # Spaltennamen trimmen (gegen Leerzeichen-Fehler)
    df_summary.columns = df_summary.columns.str.strip()
    df_ts.columns = df_ts.columns.str.strip()

    # 2. AGGRESSIVE REINIGUNG
    df_summary['auc_delta'] = brute_force_numeric(df_summary['auc_delta'])
    df_summary['temp_aoi_a_max'] = brute_force_numeric(df_summary['temp_aoi_a_max'])
    df_summary['group_id'] = brute_force_numeric(df_summary['group_id'])

    # In den Zeitreihen die Baseline-Spalte reinigen
    temp_col = 'temp_aoi_a_avg' if 'temp_aoi_a_avg' in df_ts.columns else 'temp_aoi_a_max'
    df_ts[temp_col] = brute_force_numeric(df_ts[temp_col])

    # 3. BASELINE BERECHNEN (Phase 0)
    baseline_list = []
    for subj_id in df_summary['id'].unique():
        # ID-Format vereinheitlichen (Float zu Int zu Int)
        sid = int(float(subj_id))
        base_rows = df_ts[(df_ts['id'].astype(float).astype(int) == sid) & (df_ts['time_phase'] == 0)]
        if not base_rows.empty:
            base_avg = base_rows[temp_col].mean()
            baseline_list.append({'id': sid, 'base_avg': base_avg})

    df_base = pd.DataFrame(baseline_list)

    # 4. MERGE (Wir machen beide IDs zu Int)
    df_summary['id'] = df_summary['id'].astype(float).astype(int)
    df = df_summary.merge(df_base, on='id')

    if df.empty:
        print("FEHLER: Merge fehlgeschlagen. IDs prüfen!")
    else:
        # 5. BERECHNUNGEN
        df['reiz_delta'] = df['temp_aoi_a_max'] - df['base_avg']

        # Nur gültige group_ids (0 und 1) behalten
        df = df[df['group_id'].isin([2])]

        print("\n--- Deskriptive Statistik der AUC ---")
        # Groupby und Aggregation
        res_table = df.groupby('group_id')['auc_delta'].agg(['mean', 'std', 'count']).round(2)
        print(res_table)

        # 6. BIOMETRISCHE KENNWERTE
        verum = df[df['group_id'] == 1]['auc_delta'].dropna()
        sham = df[df['group_id'] == 0]['auc_delta'].dropna()

        if len(verum) > 1 and len(sham) > 1:
            pooled_sd = np.sqrt(((len(verum)-1)*verum.var() + (len(sham)-1)*sham.var()) / (len(verum)+len(sham)-2))
            d = (verum.mean() - sham.mean()) / pooled_sd
            rmse_reiz = np.sqrt(np.mean(df['reiz_delta'].dropna()**2))

            print("\n--- Finale Ergebnisse für die Thesis ---")
            print(f"Gepoolte SD (AUC):           {pooled_sd:.2f}")
            print(f"Effektstärke Cohen's d:      {d:.4f}")
            print(f"RMSE (Hitzereiz-Präzision):  {rmse_reiz:.4f} K")
        else:
            print("\nFEHLER: Zu wenig Datenpunkte pro Gruppe für SD-Berechnung.")

except Exception as e:
    print(f"Kritischer Fehler: {e}")

