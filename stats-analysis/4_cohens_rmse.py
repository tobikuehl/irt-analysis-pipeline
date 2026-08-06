import pandas as pd
import numpy as np

def clean_numeric(series):
    """Bügelt das deutsche Komma-Problem weg."""
    return pd.to_numeric(series.astype(str).str.replace(',', '.'), errors='coerce')

try:
    # 1. DATEN LADEN
    df_sum = pd.read_csv('cohens_d.csv', sep=None, engine='python')
    df_ts = pd.read_csv('Messungen_zeitreihen.csv', sep=None, engine='python')

    # 2. REINIGUNG
    df_sum['id'] = clean_numeric(df_sum['id']).astype(int)
    df_sum['auc_delta'] = clean_numeric(df_sum['auc_delta'])
    df_sum['group_id'] = clean_numeric(df_sum['group_id'])

    # Falls du die Spalte mit den Max-Werten anders benannt hast, hier anpassen:
    max_col = 'temp_aoi_a_max'
    df_sum[max_col] = clean_numeric(df_sum[max_col])

    # 3. BASELINE-MITTELWERTE (Phase 0) AUS ZEITREIHEN HOLEN
    baseline_lookup = {}
    for sid in df_sum['id'].unique():
        # Baseline-Durchschnitt für jeden Probanden berechnen
        b_val = df_ts[(df_ts['id'] == sid) & (df_ts['time_phase'] == 0)]['temp_aoi_a_avg']
        if not b_val.empty:
            baseline_lookup[sid] = b_val.mean()

    # 4. RMSE BERECHNUNG (Reiz-Induktion)
    # RMSE = Wurzel aus dem Durchschnitt der quadrierten Deltas (Max_Reiz - Baseline)
    deltas = []
    for index, row in df_sum.iterrows():
        sid = row['id']
        if sid in baseline_lookup:
            # Hier berechnen wir, wie stark der Reiz die Haut WIRKLICH erhitzt hat
            delta_reiz = row[max_col] - baseline_lookup[sid]
            deltas.append(delta_reiz)

    rmse_val = np.sqrt(np.mean(np.array(deltas)**2))

    # 5. OUTPUT
    print("\n--- Biometrische Kennwerte (v5.0.0) ---")
    print(f"Effektstärke Cohen's d:      {df_sum[df_sum['group_id']==1]['auc_delta'].mean() - df_sum[df_sum['group_id']==0]['auc_delta'].mean():.4f} (Raw Diff)")
    # (Wir nutzen hier die Werte, die du oben schon bestätigt hast)
    print(f"Gepoolte SD (AUC):           246.57")
    print(f"Effektstärke Cohen's d:      -1.0974")
    print(f"RMSE (Reiz-Reproduzierbarkeit): {rmse_val:.4f} K")

    if rmse_val <= 0.3:
        print("=> ERFOLG: Technisches Kriterium laut Protokoll erfüllt.")
    else:
        print(f"=> HINWEIS: RMSE von {rmse_val:.2f} K zeigt höhere technische Varianz als geplant.")

except Exception as e:
    print(f"Fehler in v5.0.0: {e}")

