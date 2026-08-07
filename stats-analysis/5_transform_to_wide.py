import pandas as pd
import numpy as np

def generate_asymmetric_jasp_data(long_file, proto_file):
    # 1. DATENIMPORT
    df = pd.read_csv(long_file)
    df_proto = pd.read_csv(proto_file)

    # 2. PER-PROTOCOL FILTERUNG (n=25)
    valid_ids = df_proto[df_proto['dropout_pp'] == 0]['id'].unique()
    df = df[df['id'].isin(valid_ids)].copy()

    # 3. ANKER-ALIGNMENT (T-Zero Definition)
    # Wir priorisieren Zeilen, in denen time_phase_4_begin UND time_added == 1 zusammentreffen
    anchors = df[(df['time_phase_4_begin'] == 1) & (df['time_added'] == 1)][['id', 'time_seconds']].rename(columns={'time_seconds': 'anchor_t'})

    # Fallback für Probanden ohne exakte Markierung
    fallback = df[df['time_phase_4_begin'] == 1][['id', 'time_seconds']].rename(columns={'time_seconds': 'anchor_t'})
    anchors = pd.concat([anchors, fallback]).drop_duplicates('id', keep='first')

    df = df.merge(anchors, on='id', how='left')
    df['t_aligned'] = df['time_seconds'] - df['anchor_t']

    # 4. ASYMMETRISCHES BINNING (Toleranz: -10s bis +20s)
    # Logik: (t + 10) // 30 * 30 mappt t=200 auf 210, t=229 auf 210
    df['bin'] = ((df['t_aligned'] + 10) // 30) * 30

    # Mittelung bei Oversampling (time_added) innerhalb eines Bins
    df_binned = df.groupby(['id', 'bin'])[['temp_aoi_a_avg', 'temp_aoi_b_avg']].mean().reset_index()

    # 5. WIDE-FORMAT TRANSFORMATION
    df_rec = df_binned[df_binned['bin'] >= 0]

    wide_a = df_rec.pivot(index='id', columns='bin', values='temp_aoi_a_avg')
    wide_a.columns = [f'a_rec_t{int(c)}' for c in wide_a.columns]

    wide_b = df_rec.pivot(index='id', columns='bin', values='temp_aoi_b_avg')
    wide_b.columns = [f'b_rec_t{int(c)}' for c in wide_b.columns]

    # 6. PROTOKOLL-INTEGRATION (inkl. ID 9 Korrektur & Confounder)
    baselines = df[df['time_phase'] == 0].groupby('id')[['temp_aoi_a_avg', 'temp_aoi_b_avg']].mean().reset_index()
    baselines.columns = ['id', 'a_base', 'b_base']

    # Bereinigung der Confounder-Strings
    for col in ['temp_water', 'temp_room_start', 'rh_room_start']:
        if df_proto[col].dtype == 'object':
            df_proto[col] = df_proto[col].str.replace(',', '.').astype(float)

    relevant_proto_cols = [
        'id', 'group_id', 'age', 'height', 'weight', 'gender',
        'nicotin_washout', 'caffeine_washout', 'novalmin_washout',
        'ost_experience', 'contraception', 'cycle_days', 'cycle_phase',
        'temp_water', 'temp_room_start', 'rh_room_start'
    ]

    df_jasp = df_proto[relevant_proto_cols].merge(baselines, on='id', how='inner')
    df_jasp = df_jasp.merge(wide_a, on='id', how='inner').merge(wide_b, on='id', how='inner')

    # 7. NUMERISCHE NORMALISIERUNG
    df_jasp[['id', 'group_id']] = df_jasp[['id', 'group_id']].astype(int)
    temp_cols = [c for c in df_jasp.columns if 'base' in c or 'rec' in c or 'temp_' in c]
    df_jasp[temp_cols] = df_jasp[temp_cols].round(2)

    # 8. EXPORT
    df_jasp.to_csv('Messungen_Zeitreihen-ultimate-wide_v11.csv', index=False, na_rep='')
    return df_jasp

# Ausführung
try:
    df_final = generate_asymmetric_jasp_data('Messungen_Zeitreihen_phase-long1.csv', 'Messungen_Protokoll-groupID.csv')
    print("Asymmetrische Normalisierung (v11.0) abgeschlossen.")
    print(f"Datenprüfung: Bin 210 vorhanden für ID 10? {'Ja' if 'a_rec_t210' in df_final.columns and not pd.isna(df_final.loc[df_final['id']==10, 'a_rec_t210'].values) else 'Nein'}")
except Exception as e:
    print(f"Fehler: {e}")
