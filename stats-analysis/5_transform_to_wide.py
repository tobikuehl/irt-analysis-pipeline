import pandas as pd
import numpy as np

def process_aligned_data(filename):
    # 1. DATEN LADEN
    df = pd.read_csv(filename, sep=',')
    df_proto = pd.read_csv('Messungen_Protokoll-groupID.csv', sep=',')

    # Per-Protocol Filter (Ausschluss IDs 1-4, 6-8, 26 wegen fehlender Baseline)
    valid_ids = df_proto[df_proto['dropout_pp'] == 0]['id'].unique()
    df = df[df['id'].isin(valid_ids)].copy()

    # 2. ANKER-ZEITEN DEFINIEREN
    # Wir suchen für jede ID den Zeitpunkt, an dem phase_4_begin markiert ist
    anchors = df[df['time_phase_4_begin'] == 1][['id', 'time_seconds']].rename(columns={'time_seconds': 'anchor_time'})

    # Falls eine ID keinen Anker hat (Protokollfehler), nutzen wir den ersten Phase-4-Eintrag
    fallback_anchors = df[df['time_phase'] == 4].groupby('id')['time_seconds'].min().reset_index().rename(columns={'time_seconds': 'anchor_time'})

    final_anchors = pd.merge(fallback_anchors, anchors, on='id', how='left')
    final_anchors['anchor_time'] = final_anchors['anchor_time_y'].fillna(final_anchors['anchor_time_x'])

    # 3. ZEITREIHEN AUSRICHTEN
    df = df.merge(final_anchors[['id', 'anchor_time']], on='id')
    df['time_aligned'] = df['time_seconds'] - df['anchor_time']

    # 4. BINNING FÜR JASP (30s-Raster)
    # Wir runden die ausgerichtete Zeit auf das nächste 30s-Intervall
    df['time_bin'] = (df['time_aligned'] / 30).round().astype(int) * 30

    # Extra-Bilder und Jitter glätten durch Mittelung pro Bin
    df_binned = df.groupby(['id', 'time_bin'])[['temp_aoi_a_avg', 'temp_aoi_b_avg']].mean().reset_index()

    # 5. TRANSFORMATION INS WIDE-FORMAT (Nur für Phase 4: Recovery)
    # Wir nehmen nur Werte ab dem Anker (t >= 0)
    df_recovery = df_binned[df_binned['time_bin'] >= 0]

    wide_a = df_recovery.pivot(index='id', columns='time_bin', values='temp_aoi_a_avg')
    wide_a.columns = [f'rec_t{c}' for c in wide_a.columns]

    # 6. BASELINE (Phase 0) HINZUFÜGEN
    # Wir nutzen den Mittelwert der gesamten Phase 0 als stabilen Referenzwert
    baselines = df[df['time_phase'] == 0].groupby('id')['temp_aoi_a_avg'].mean().reset_index().rename(columns={'temp_aoi_a_avg': 'baseline_avg'})

    # 7. FINALER EXPORT
    df_wide = df_proto[['id', 'group_id']].merge(baselines, on='id').merge(wide_a, on='id')
    df_wide.to_csv('Messungen_Zeitreihen-final-wide.csv', index=False)

    return df_wide

try:
    df_final = process_aligned_data('Messungen_Zeitreihen_phase-long.csv')
    print("Alignment v5.8.0 erfolgreich. Datei 'Messungen_Zeitreihen-final-wide.csv' erstellt.")
except Exception as e:
    print(f"Fehler: {e}")
