"""
DATEI: Datenaufbereitung_und_AUC.py
PROJEKT: Pilotstudie DRKS00040377 (Flare-Inhibition)
AUTOR: Tobias Kühl
BESCHREIBUNG:
1. Automatisierte Bereinigung von Rohdaten (Dezimalkomma-Korrektur).
2. Berechnung des Hitzereiz-Deltas und RMSE zur technischen Validierung.
3. Statistische Deskription und Berechnung der Effektstärke Cohen's d (AUC).
"""

import pandas as pd
import numpy as np
import re

def super_clean(series):
    """
    Sichert die numerische Integrität durch Entfernung von Sonderzeichen
    und Konvertierung deutscher Dezimaltrennzeichen.
    """
    def clean_val(x):
        if pd.isna(x): return np.nan
        s = re.sub(r'[^0-9.,-]', '', str(x))
        s = s.replace(',', '.')
        try:
            return float(s)
        except:
            return np.nan
    return series.apply(clean_val)

try:
    # 1. DATENIMPORT (Automatisierte Trennzeichen-Erkennung)
    df_sum_raw = pd.read_csv('tbl-auc_delta.csv', sep=None, engine='python')
    df_ts_raw = pd.read_csv('tbl-messungen_wide.csv', sep=None, engine='python')

    # Spalten-Bereinigung (Entfernung von Whitespaces in Headern)
    df_sum_raw.columns = df_sum_raw.columns.str.strip()
    df_ts_raw.columns = df_ts_raw.columns.str.strip()

    # 2. NUMERISCHE TRANSFORMATION
    df_sum = df_sum_raw.copy()
    df_sum['id'] = super_clean(df_sum['id']).astype(int)
    df_sum['auc_delta'] = super_clean(df_sum['auc_delta'])
    df_sum['group_id'] = super_clean(df_sum['group_id']).astype(int)
    df_sum['temp_aoi_a_max'] = super_clean(df_sum['temp_aoi_a_max'])

    df_ts = df_ts_raw.copy()
    df_ts['id'] = super_clean(df_ts['id']).astype(int)
    # Fallback-Logik für AOI-Spaltennamen
    temp_col = 'temp_aoi_a_avg' if 'temp_aoi_a_avg' in df_ts.columns else 'temp_aoi_a_max'
    df_ts[temp_col] = super_clean(df_ts[temp_col])

    # 3. EXTRAKTION DER INDIVIDUELLEN BASELINES (Phase 0)
    baseline_list = []
    for sid in df_sum['id'].unique():
        base_rows = df_ts[(df_ts['id'] == sid) & (df_ts['time_phase'] == 0)]
        if not base_rows.empty:
            baseline_list.append({'id': sid, 'base_avg': base_rows[temp_col].mean()})

    df_base = pd.DataFrame(baseline_list)
    df_final = df_sum.merge(df_base, on='id')

    # 4. REIZ-VALIDIERUNG (RMSE)
    # Berechnung der durchschnittlichen Reizintensität (Delta T)
    df_final['reiz_delta'] = df_final['temp_aoi_a_max'] - df_final['base_avg']
    rmse_reiz = np.sqrt(np.mean(df_final['reiz_delta'].dropna()**2))

    # 5. KENNWERTE FÜR DEN ERGEBNISTEIL
    stats = df_final.groupby('group_id')['auc_delta'].agg(['mean', 'std', 'count']).round(2)

    # Effektstärke Cohen's d (Gepoolte Standardabweichung)
    verum = df_final[df_final['group_id'] == 1]['auc_delta'].dropna()
    sham = df_final[df_final['group_id'] == 0]['auc_delta'].dropna()
    n1, n2 = len(verum), len(sham)
    pooled_sd = np.sqrt(((n1-1)*verum.var() + (n2-1)*sham.var()) / (n1+n2-2))
    d = (verum.mean() - sham.mean()) / pooled_sd

    print("--- Deskriptive Statistik (AUC) ---")
    print(stats)
    print(f"\nBiometrische Kennwerte:")
    print(f"Cohen's d: {d:.4f}")
    print(f"RMSE (Reiz-Intensität): {rmse_reiz:.4f} K")

except Exception as e:
    print(f"Fehler bei der Datenverarbeitung: {e}")

