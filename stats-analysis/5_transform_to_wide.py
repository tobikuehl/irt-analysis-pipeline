import pandas as pd
import numpy as np

def generate_full_analysis_table(long_file, proto_file):
    df = pd.read_csv(long_file)
    df_proto = pd.read_csv(proto_file)

    # 1. Per-Protocol Filter (n=25)
    valid_ids = df_proto[df_proto['dropout_pp'] == 0]['id'].unique()
    df = df[df['id'].isin(valid_ids)].copy()

    # 2. Asymmetrisches Binning (wie v11.0)
    anchors = df[(df['time_phase_4_begin'] == 1) & (df['time_added'] == 1)][['id', 'time_seconds']].rename(columns={'time_seconds': 'anchor_t'})
    fallback = df[df['time_phase_4_begin'] == 1][['id', 'time_seconds']].rename(columns={'time_seconds': 'anchor_t'})
    anchors = pd.concat([anchors, fallback]).drop_duplicates('id', keep='first')
    df = df.merge(anchors, on='id', how='left')
    df['t_aligned'] = df['time_seconds'] - df['anchor_t']
    df['bin'] = ((df['t_aligned'] + 10) // 30) * 30
    df_binned = df.groupby(['id', 'bin'])[['temp_aoi_a_avg', 'temp_aoi_b_avg']].mean().reset_index()

    # 3. Wide-Transformation
    df_rec = df_binned[df_binned['bin'] >= 0]
    wide_a = df_rec.pivot(index='id', columns='bin', values='temp_aoi_a_avg')
    wide_a.columns = [f'a_rec_t{int(c)}' for c in wide_a.columns]
    wide_b = df_rec.pivot(index='id', columns='bin', values='temp_aoi_b_avg')
    wide_b.columns = [f'b_rec_t{int(c)}' for c in wide_b.columns]

    # 4. Erfassung aller Protokoll-Parameter (inkl. CEQ & Deblinding)
    # Wir nehmen alle Spalten, die für die Interpretation wichtig sind
    proto_cols = [
        'id', 'group_id', 'age', 'height', 'weight', 'gender',
        'nicotin_washout', 'caffeine_washout', 'combined_acclimatization_phase',
        'temp_water', 'temp_room_start', 'rh_room_start',
        'ceq_pre_q4_calc', 'ceq_pre_q6_calc', 'ceq_post_4_calc', 'ceq_post_6_calc',
        'deblinding_check', 'vas_1', 'vas_2', 'vas_6'
    ]

    # Vorbereitung der Protokoll-Daten (Kommata-Fix)
    for col in ['temp_water', 'temp_room_start', 'rh_room_start', 'ceq_pre_q4_calc', 'ceq_pre_q6_calc', 'ceq_post_4_calc', 'ceq_post_6_calc']:
        if df_proto[col].dtype == 'object':
            df_proto[col] = df_proto[col].str.replace(',', '.').astype(float)

    # 5. Zusammenführung
    baselines = df[df['time_phase'] == 0].groupby('id')[['temp_aoi_a_avg', 'temp_aoi_b_avg']].mean().reset_index()
    baselines.columns = ['id', 'a_base', 'b_base']

    df_final = df_proto[proto_cols].merge(baselines, on='id', how='inner')
    df_final = df_final.merge(wide_a, on='id', how='inner').merge(wide_b, on='id', how='inner')

    # Numerische Politur
    df_final[['id', 'group_id']] = df_final[['id', 'group_id']].astype(int)
    # Runden auf instrumentelle Präzision
    temp_cols = [c for c in df_final.columns if 'base' in c or 'rec' in c or 'temp_' in c]
    df_final[temp_cols] = df_final[temp_cols].round(2)
    df_final[[c for c in df_final.columns if 'calc' in c]] = df_final[[c for c in df_final.columns if 'calc' in c]].round(1)

    df_final.to_csv('Messungen_Zeitreihen-ultimate-wide_v12.csv', index=False, na_rep='')
    return df_final

try:
    df_v12 = generate_full_analysis_table('Messungen_Zeitreihen_phase-long1.csv', 'Messungen_Protokoll-groupID.csv')
    print("Version 12.0 erstellt. Alle psychometrischen Daten und Confounder integriert.")
except Exception as e:
    print(f"Fehler: {e}")
