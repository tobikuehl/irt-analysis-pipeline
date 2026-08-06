import pandas as pd
import numpy as np

# 1. FUNKTION ZUM EINLESEN (behandelt Komma und Punkt)
def smart_read(file):
    try:
        # Erster Versuch: Standard-CSV
        return pd.read_csv(file, sep=',', decimal='.')
    except:
        # Zweiter Versuch: Deutsches Format (Semicolon & Komma)
        return pd.read_csv(file, sep=';', decimal=',')

# 2. DATEN LADEN
try:
    df_cohen = smart_read('cohens_d.csv')
    df_ts = smart_read('Messungen_zeitreihen.csv')

    # Sicherstellen, dass auc_delta numerisch ist (Zwingt Umwandlung)
    if df_cohen['auc_delta'].dtype == 'object':
        df_cohen['auc_delta'] = df_cohen['auc_delta'].str.replace(',', '.').astype(float)

    # 3. HITZEREIZ-DELTA BERECHNEN (aus Zeitreihen)
    reiz_deltas = []
    for subj_id in df_cohen['id'].unique():
        subj_data = df_ts[df_ts['id'] == subj_id]
        # Baseline (Phase 0) Mittelwert
        base_avg = subj_data[subj_data['time_phase'] == 0]['temp_aoi_a_avg'].mean()
        # Post-Reiz (Phase 1) erster Wert
        t1_val = subj_data[subj_data['time_phase'] == 1]['temp_aoi_a_avg'].iloc
        reiz_deltas.append({'id': subj_id, 'reiz_delta': t1_val - base_avg})

    df_reiz = pd.DataFrame(reiz_deltas)
    df = df_cohen.merge(df_reiz, on='id')

    # 4. STATISTIK PRO GRUPPE (group_id: 1=Verum, 0=Sham)
    stats = df.groupby('group_id')['auc_delta'].agg(['mean', 'std', 'count'])
    print("\n--- Deskriptive Statistik der AUC ---")
    print(stats)

    # 5. COHEN'S D BERECHNUNG
    verum = df[df['group_id'] == 1]['auc_delta']
    sham = df[df['group_id'] == 0]['auc_delta']
    pooled_sd = np.sqrt(((len(verum)-1)*verum.var() + (len(sham)-1)*sham.var()) / (len(verum)+len(sham)-2))
    d = (verum.mean() - sham.mean()) / pooled_sd

    # 6. RMSE BERECHNUNG (Erfolgskriterium Reizsetzung)
    rmse_reiz = np.sqrt(np.mean(df['reiz_delta']**2))

    print("\n--- Biometrische Kennwerte ---")
    print(f"Effektstärke Cohen's d (AUC): {d:.4f}")
    print(f"RMSE (Hitzereiz-Präzision):  {rmse_reiz:.4f} K")
    if rmse_reiz <= 0.3:
        print("=> Erfolgskriterium (RMSE <= 0.3 K) ERFÜLLT.")
    else:
        print("=> Erfolgskriterium knapp verfehlt (Varianz prüfen).")

except Exception as e:
    print(f"Fehler: {e}")
