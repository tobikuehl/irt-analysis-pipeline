import pandas as pd
import numpy as np

def ultra_clean(df):
    """Die erfolgreiche Methode aus v4: Säubert Spaltennamen und Zellinhalte."""
    # 1. Spaltennamen von Leerzeichen befreien
    df.columns = df.columns.str.strip()

    # 2. Zellinhalte bereinigen
    for col in df.columns:
        if df[col].dtype == 'object':
            # Entferne Anführungszeichen, korrigiere Dezimalkomma, entferne Leerzeichen
            df[col] = df[col].astype(str).str.replace('"', '').str.replace(',', '.').str.strip()

        # Umwandlung in numerische Werte erzwingen (ungültige werden NaN)
        df[col] = pd.to_numeric(df[col], errors='coerce')

    # 3. ID als Ganzzahl (Integer) normieren
    if 'id' in df.columns:
        df = df.dropna(subset=['id'])
        df['id'] = df['id'].astype(int)
    return df

try:
    # 1. DATEN LADEN
    df_sum_raw = pd.read_csv('cohens_d.csv', sep=None, engine='python')
    df_ts_raw = pd.read_csv('Messungen_zeitreihen.csv', sep=None, engine='python')

    # 2. DIE ERFOLGREICHE REINIGUNG ANWENDEN
    df_sum = ultra_clean(df_sum_raw)
    df_ts = ultra_clean(df_ts_raw)

    # 3. BASELINE-MITTELWERTE (Phase 0) AUS ZEITREIHEN EXTRAHIEREN
    temp_col = 'temp_aoi_a_avg' if 'temp_aoi_a_avg' in df_ts.columns else 'temp_aoi_a_max'
    baseline_list = []

    for sid in df_sum['id'].unique():
        # Mittelwert der Phase 0 für jeden Probanden berechnen [1]
        base_rows = df_ts[(df_ts['id'] == sid) & (df_ts['time_phase'] == 0)]
        if not base_rows.empty:
            base_avg = base_rows[temp_col].mean()
            baseline_list.append({'id': sid, 'base_avg': base_avg})

    df_base = pd.DataFrame(baseline_list)

    # 4. TABELLEN ZUSAMMENFÜHREN
    df_final = df_sum.merge(df_base, on='id')

    # 5. REIZ-VALIDIERUNG BERECHNEN (Spitzentemperatur vs. Baseline)
    # Nutzt deinen manuell eingetragenen temp_aoi_a_max aus cohens_d.csv [2]
    df_final['reiz_delta'] = df_final['temp_aoi_a_max'] - df_final['base_avg']

    # 6. OUTPUT DER ERGEBNISSE
    print("\n--- Deskriptive Statistik der AUC ---")
    # Gruppierung (0=Sham, 1=Verum) [3]
    stats = df_final.groupby('group_id')['auc_delta'].agg(['mean', 'std', 'count']).round(2)
    print(stats)

    # Cohen's d Berechnung
    verum = df_final[df_final['group_id'] == 1]['auc_delta'].dropna()
    sham = df_final[df_final['group_id'] == 0]['auc_delta'].dropna()

    pooled_sd = np.sqrt(((len(verum)-1)*verum.var() + (len(sham)-1)*sham.var()) / (len(verum)+len(sham)-2))
    d = (verum.mean() - sham.mean()) / pooled_sd

    # RMSE (Root Mean Square Error der Reizsetzung) [4]
    rmse_reiz = np.sqrt(np.mean(df_final['reiz_delta'].dropna()**2))

    print("\n--- Biometrische Kennwerte (v5.1.0) ---")
    print(f"Gepoolte SD (AUC):           {pooled_sd:.2f}")
    print(f"Effektstärke Cohen's d:      {d:.4f}")
    print(f"RMSE (Hitzereiz-Präzision):  {rmse_reiz:.4f} K")

    if rmse_reiz <= 0.3:
        print("=> ERFOLG: Technisches Kriterium (RMSE <= 0.3 K) erfüllt.")
    else:
        print(f"=> HINWEIS: RMSE von {rmse_reiz:.2f} K zeigt Varianz in der Reizsetzung.")

except Exception as e:
    print(f"Kritischer Fehler: {e}")
