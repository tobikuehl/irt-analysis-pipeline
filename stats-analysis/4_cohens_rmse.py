import pandas as pd
import numpy as np

def ultra_clean(df):
    # 1. Alle Spaltennamen von Leerzeichen befreien (sehr häufiger Fehler!)
    df.columns = df.columns.str.strip()

    # 2. Datentypen bereinigen
    for col in df.columns:
        if df[col].dtype == 'object':
            # Entferne Anführungszeichen und ersetze Komma durch Punkt
            df[col] = df[col].astype(str).str.replace('"', '').str.replace(',', '.').str.strip()

        # Versuche in Zahl umzuwandeln, ungültige Werte werden NaN
        df[col] = pd.to_numeric(df[col], errors='coerce')

    # 3. ID als Ganzzahl fixieren
    if 'id' in df.columns:
        df = df.dropna(subset=['id'])
        df['id'] = df['id'].astype(int)
    return df

try:
    # Daten laden (sep=None erkennt , oder ; automatisch)
    df_summary = pd.read_csv('cohens_d.csv', sep=None, engine='python')
    df_ts = pd.read_csv('Messungen_zeitreihen.csv', sep=None, engine='python')

    # Radikale Reinigung
    df_summary = ultra_clean(df_summary)
    df_ts = ultra_clean(df_ts)

    # Baseline-Mittelwerte (Phase 0)
    baseline_list = []
    # Spaltennamen-Check für Zeitreihen (manchmal heißt es anders)
    temp_col = 'temp_aoi_a_avg' if 'temp_aoi_a_avg' in df_ts.columns else 'temp_aoi_a_max'

    for subj_id in df_summary['id'].unique():
        base_rows = df_ts[(df_ts['id'] == subj_id) & (df_ts['time_phase'] == 0)]
        if not base_rows.empty:
            base_avg = base_rows[temp_col].mean()
            baseline_list.append({'id': int(subj_id), 'base_avg': base_avg})

    df_base = pd.DataFrame(baseline_list)

    # Zusammenführen
    df = df_summary.merge(df_base, on='id')

    if df.empty:
        print("FEHLER: Keine Übereinstimmung der IDs nach der Reinigung!")
    else:
        # Hitzereiz-Delta (Wichtig: group_id muss 0 oder 1 sein)
        df['reiz_delta'] = df['temp_aoi_a_max'] - df['base_avg']

        # Statistik (Wir erzwingen hier group_id als Integer)
        df['group_id'] = df['group_id'].astype(int)

        print("\n--- Deskriptive Statistik der AUC ---")
        stats = df.groupby('group_id')['auc_delta'].agg(['mean', 'std', 'count']).round(2)
        print(stats)

        # Cohen's d
        verum = df[df['group_id'] == 1]['auc_delta'].dropna()
        sham = df[df['group_id'] == 0]['auc_delta'].dropna()

        if len(verum) > 0 and len(sham) > 0:
            pooled_sd = np.sqrt(((len(verum)-1)*verum.var() + (len(sham)-1)*sham.var()) / (len(verum)+len(sham)-2))
            d = (verum.mean() - sham.mean()) / pooled_sd
            rmse_reiz = np.sqrt(np.mean(df['reiz_delta'].dropna()**2))

            print("\n--- Biometrische Kennwerte für die Thesis ---")
            print(f"Analysierte Fallzahl (PP):   {len(df)}")
            print(f"Gepoolte SD (AUC):           {pooled_sd:.2f}")
            print(f"Effektstärke Cohen's d:      {d:.4f}")
            print(f"RMSE (Hitzereiz-Präzision):  {rmse_reiz:.4f} K")
        else:
            print("\nFEHLER: Eine der Gruppen (Verum/Sham) enthält keine berechenbaren Daten.")

except Exception as e:
    print(f"Kritischer Fehler: {e}")
