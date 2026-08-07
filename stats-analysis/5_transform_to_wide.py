import pandas as pd
import numpy as np

def generate_cleaned_jasp_data(long_file, proto_file):
    # 1. Datenimport
    df = pd.read_csv(long_file)
    df_proto = pd.read_csv(proto_file)

    # 2. Per-Protocol Filterung (n=25)
    valid_ids = df_proto[df_proto['dropout_pp'] == 0]['id'].unique()
    df = df[df['id'].isin(valid_ids)].copy()

    # 3. Anker-Alignment (Phase 4 Start)
    anchors = df[df['time_phase_4_begin'] == 1][['id', 'time_seconds']].rename(columns={'time_seconds': 'anchor_t'})
    df = df.merge(anchors, on='id', how='left')
    df['t_aligned'] = df['time_seconds'] - df['anchor_t']

    # 4. Binning (30s-Raster) zur Stabilisierung thermischer Oszillationen
    df['bin'] = (df['t_aligned'] / 30).round().astype(int) * 30
    df_binned = df.groupby(['id', 'bin'])[['temp_aoi_a_avg', 'temp_aoi_b_avg']].mean().reset_index()

    # 5. Wide-Format Transformation (Recovery-Phase)
    df_rec = df_binned[df_binned['bin'] >= 0]

    wide_a = df_rec.pivot(index='id', columns='bin', values='temp_aoi_a_avg')
    wide_a.columns = [f'a_rec_t{int(c)}' for c in wide_a.columns]

    wide_b = df_rec.pivot(index='id', columns='bin', values='temp_aoi_b_avg')
    wide_b.columns = [f'b_rec_t{int(c)}' for c in wide_b.columns]

    # 6. Integration der Baseline-Mittelwerte (Phase 0)
    baselines = df[df['time_phase'] == 0].groupby('id')[['temp_aoi_a_avg', 'temp_aoi_b_avg']].mean().reset_index()
    baselines.columns = ['id', 'a_base', 'b_base']

    # 7. Zusammenführung und numerische Formatierung
    df_jasp = df_proto[['id', 'group_id']].merge(baselines, on='id', how='inner')
    df_jasp = df_jasp.merge(wide_a, on='id').merge(wide_b, on='id')

    # Identifikatoren explizit als Ganzzahlen (Integer)
    df_jasp['id'] = df_jasp['id'].astype(int)
    df_jasp['group_id'] = df_jasp['group_id'].astype(int)

    # Begrenzung der Temperaturwerte auf zwei Nachkommastellen
    # (Erhalt der Information aus Mittelwertbildungen bei 0,1 °C Sensorauflösung)
    temp_cols = [c for c in df_jasp.columns if 'base' in c or 'rec' in c]
    df_jasp[temp_cols] = df_jasp[temp_cols].round(2)

    # 8. Export
    df_jasp.to_csv('Messungen_Zeitreihen-final-wide_v7.csv', index=False, na_rep='NaN')
    return df_jasp

try:
    df_final = generate_cleaned_jasp_data('Messungen_Zeitreihen_phase-long1.csv', 'Messungen_Protokoll-groupID.csv')
    print("Numerische Normalisierung abgeschlossen. Datei 'Messungen_Zeitreihen-final-wide_v7.csv' erstellt.")
except Exception as e:
    print(f"Fehler bei der Datenverarbeitung: {e}")
