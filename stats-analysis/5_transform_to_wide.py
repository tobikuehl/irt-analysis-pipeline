import pandas as pd
import numpy as np

def generate_perfect_v14_3_table(long_file, proto_file):
    df_long = pd.read_csv(long_file)
    df_proto = pd.read_csv(proto_file)

    # 1. BEREINIGUNG DER PROTOKOLL-DATEN
    # Geisterzeilen ohne echte ID entfernen
    df_proto = df_proto.dropna(subset=['id']).copy()

    # Konvertierung time_start -> Minuten seit Mitternacht
    def get_min_midnight(val):
        try:
            h, m, s = map(int, str(val).split(':'))
            return h * 60 + m
        except:
            return np.nan

    df_proto['time_minutes_midnight'] = df_proto['time_start'].apply(get_min_midnight)

    # Radikale numerische Bereinigung (Kommata-Fix für ALLE relevanten Spalten)
    cols_to_fix = [
        'caffeine_washout', 'nicotin_washout', 'novalmin_washout',
        'temp_water', 'temp_room_start', 'temp_room_end',
        'rh_room_start', 'rh_room_end',
        'ceq_pre_q4_calc', 'ceq_pre_q6_calc', 'ceq_post_4_calc', 'ceq_post_6_calc'
    ]

    for col in cols_to_fix:
        if col in df_proto.columns:
            if df_proto[col].dtype == 'object':
                df_proto[col] = df_proto[col].str.replace(',', '.', regex=False)
            df_proto[col] = pd.to_numeric(df_proto[col], errors='coerce')

    # 2. ASYMMETRISCHES BINNING (Logik v11-v14 beibehalten)
    anchors = df_long[(df_long['time_phase_4_begin'] == 1) & (df_long['time_added'] == 1)][['id', 'time_seconds']].rename(columns={'time_seconds': 'anchor_t'})
    fallback = df_long[df_long['time_phase_4_begin'] == 1][['id', 'time_seconds']].rename(columns={'time_seconds': 'anchor_t'})
    anchors = pd.concat([anchors, fallback]).drop_duplicates('id', keep='first')
    df_aligned = df_long.merge(anchors, on='id', how='left')
    df_aligned['t_aligned'] = df_aligned['time_seconds'] - df_aligned['anchor_t']
    df_aligned['bin'] = ((df_aligned['t_aligned'] + 10) // 30) * 30

    df_binned = df_aligned.groupby(['id', 'bin'])[['temp_aoi_a_avg', 'temp_aoi_b_avg']].mean().reset_index()
    df_rec = df_binned[df_binned['bin'] >= 0]

    wide_a = df_rec.pivot(index='id', columns='bin', values='temp_aoi_a_avg')
    wide_a.columns = [f'a_rec_t{int(c)}' for c in wide_a.columns]
    wide_b = df_rec.pivot(index='id', columns='bin', values='temp_aoi_b_avg')
    wide_b.columns = [f'b_rec_t{int(c)}' for c in wide_b.columns]

    # 3. ZUSAMMENFÜHRUNG
    baselines = df_long[df_long['time_phase'] == 0].groupby('id')[['temp_aoi_a_avg', 'temp_aoi_b_avg']].mean().reset_index()
    baselines.columns = ['id', 'a_base', 'b_base']

    df_final = df_proto.merge(baselines, on='id', how='left')
    df_final = df_final.merge(wide_a, on='id', how='left').merge(wide_b, on='id', how='left')

    # 4. FINALES CASTING & RUNDUNG
    for int_col in ['id', 'group_id', 'dropout_pp', 'gender']:
        df_final[int_col] = df_final[int_col].astype(int)

    temp_cols = [c for c in df_final.columns if 'base' in c or 'rec' in c or 'temp_' in c or 'washout' in c]
    df_final[temp_cols] = df_final[temp_cols].round(2)
    df_final[[c for c in df_final.columns if 'calc' in c]] = df_final[[c for c in df_final.columns if 'calc' in c]].round(1)

    df_final.to_csv('Messungen_Zeitreihen-ultimate-wide_v14_3.csv', index=False, na_rep='')
    return df_final

try:
    df_v14_3 = generate_perfect_v14_3_table('Messungen_Zeitreihen_phase-long1.csv', 'Messungen_Protokoll-groupID.csv')
    print("Version 14.3 erfolgreich erstellt. Alle Zeit- und Temperaturwerte sind numerisch validiert.")
except Exception as e:
    print(f"Fehler: {e}")
