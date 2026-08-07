import pandas as pd
import numpy as np

def generate_jasp_ready_data(long_file, proto_file):
    # 1. DATEN LADEN
    df = pd.read_csv(long_file)
    df_proto = pd.read_csv(proto_file)

    # 2. PER-PROTOCOL FILTERING (Wichtig: Nur die n=25 PP-Probanden)
    valid_ids = df_proto[df_proto['dropout_pp'] == 0]['id'].unique()
    df = df[df['id'].isin(valid_ids)].copy()

    # 3. ANKER-CALIBRATION (T-Zero Alignment)
    # Wir suchen den exakten Start von Phase 4 (Entzündungs-Beginn)
    anchors = df[df['time_phase_4_begin'] == 1][['id', 'time_seconds']].rename(columns={'time_seconds': 'anchor_t'})

    # Merge Anker und berechne ausgerichtete Zeit
    df = df.merge(anchors, on='id', how='left')
    df['t_aligned'] = df['time_seconds'] - df['anchor_t']

    # 4. BINNING (30s Raster zur Rauschunterdrückung nach Shusterman)
    df['bin'] = (df['t_aligned'] / 30).round().astype(int) * 30

    # Mittelung pro Bin (AOI A und B getrennt!)
    df_binned = df.groupby(['id', 'bin'])[['temp_aoi_a_avg', 'temp_aoi_b_avg']].mean().reset_index()

    # 5. WIDE-FORMAT TRANSFORMATION
    # Wir nehmen nur die Recovery-Phase (t >= 0)
    df_rec = df_binned[df_binned['bin'] >= 0]

    wide_a = df_rec.pivot(index='id', columns='bin', values='temp_aoi_a_avg')
    wide_a.columns = [f'a_rec_t{int(c)}' for c in wide_a.columns]

    wide_b = df_rec.pivot(index='id', columns='bin', values='temp_aoi_b_avg')
    wide_b.columns = [f'b_rec_t{int(c)}' for c in wide_b.columns]

    # 6. BASELINE INTEGRATION (Mittelwert der gesamten Phase 0)
    # Das stabilisiert den Startpunkt gegenüber kurzfristigen Schwankungen
    baselines = df[df['time_phase'] == 0].groupby('id')[['temp_aoi_a_avg', 'temp_aoi_b_avg']].mean().reset_index()
    baselines.columns = ['id', 'a_base', 'b_base']

    # 7. FINALER MERGE FÜR JASP
    df_jasp = df_proto[['id', 'group_id']].merge(baselines, on='id', how='inner')
    df_jasp = df_jasp.merge(wide_a, on='id').merge(wide_b, on='id')

    df_jasp.to_csv('Messungen_Zeitreihen-final-wide_v6.csv', index=False)
    return df_jasp

try:
    df_final = generate_jasp_ready_data('Messungen_Zeitreihen_phase-long1.csv', 'Messungen_Protokoll-groupID.csv')
    print("Transformation v6.0 erfolgreich! Datei 'Messungen_Zeitreihen-final-wide_v6.csv' ist bereit.")
    print(f"Anzahl Probanden im PP-Kollektiv: {len(df_final)}")
except Exception as e:
    print(f"Fehler: {e}")
