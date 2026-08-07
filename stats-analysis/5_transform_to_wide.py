import pandas as pd
import numpy as np

def generate_final_jasp_table(long_file, proto_file):
    # 1. Datenimport
    df = pd.read_csv(long_file)
    df_proto = pd.read_csv(proto_file)

    # 2. Per-Protocol Filterung (n=25)
    valid_ids = df_proto[df_proto['dropout_pp'] == 0]['id'].unique()
    df = df[df['id'].isin(valid_ids)].copy()

    # 3. Anker-Alignment (T-Zero für Phase 4)
    anchors = df[df['time_phase_4_begin'] == 1][['id', 'time_seconds']].rename(columns={'time_seconds': 'anchor_t'})
    df = df.merge(anchors, on='id', how='left')
    df['t_aligned'] = df['time_seconds'] - df['anchor_t']

    # 4. Binning (30s-Raster)
    df['bin'] = (df['t_aligned'] / 30).round().astype(int) * 30
    df_binned = df.groupby(['id', 'bin'])[['temp_aoi_a_avg', 'temp_aoi_b_avg']].mean().reset_index()

    # 5. Wide-Format Transformation
    df_rec = df_binned[df_binned['bin'] >= 0]
    wide_a = df_rec.pivot(index='id', columns='bin', values='temp_aoi_a_avg')
    wide_a.columns = [f'a_rec_t{int(c)}' for c in wide_a.columns]

    # 6. Baseline-Integration
    baselines = df[df['time_phase'] == 0].groupby('id')[['temp_aoi_a_avg', 'temp_aoi_b_avg']].mean().reset_index()
    baselines.columns = ['id', 'a_base', 'b_base']

    # 7. MERGE: Jetzt mit demographischen Daten (age, height, weight, gender)
    # Wir nehmen die gewünschten Spalten aus df_proto mit auf
    demo_cols = ['id', 'group_id', 'age', 'height', 'weight', 'gender']
    df_demo = df_proto[demo_cols]

    df_jasp = df_demo.merge(baselines, on='id', how='inner')
    df_jasp = df_jasp.merge(wide_a, on='id', how='inner')

    # 8. Numerische Bereinigung
    df_jasp['id'] = df_jasp['id'].astype(int)
    df_jasp['group_id'] = df_jasp['group_id'].astype(int)

    # Temperaturen runden
    temp_cols = [c for c in df_jasp.columns if 'base' in c or 'rec' in c]
    df_jasp[temp_cols] = df_jasp[temp_cols].round(2)

    # 9. Export
    df_jasp.to_csv('Messungen_Zeitreihen-final-wide_v8.csv', index=False, na_rep='NaN')
    return df_jasp

try:
    df_final = generate_final_jasp_table('Messungen_Zeitreihen_phase-long1.csv', 'Messungen_Protokoll-groupID.csv')
    print("Update v8.0 erfolgreich. 'age', 'height', 'weight' & 'gender' sind jetzt in der Wide-Tabelle.")
    print(f"Spalten im Export: {df_final.columns.tolist()[:10]}...")
except Exception as e:
    print(f"Fehler: {e}")
