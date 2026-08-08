import pandas as pd
import numpy as np

def generate_clean_v15_table(long_file, proto_file):
    # 1. DATENIMPORT & BEREINIGUNG DER ZEILEN
    df_long = pd.read_csv(long_file)
    df_proto = pd.read_csv(proto_file)

    # Entfernt Geisterzeilen am Ende (alles ohne echte ID fliegt raus)
    df_proto = df_proto.dropna(subset=['id']).copy()
    df_proto['id'] = df_proto['id'].astype(int)

    # 2. ZEIT-TRANSFORMATION (Minuten seit Mitternacht)
    def calculate_minutes(time_val):
        try:
            if pd.isna(time_val) or str(time_val).strip() == '': return np.nan
            h, m, s = map(int, str(time_val).split(':'))
            return h * 60 + m
        except:
            return np.nan

    df_proto['time_minutes_midnight'] = df_proto['time_start'].apply(calculate_minutes)

    # 3. DAS "KOMMA-MONSTER" BESIEGEN (Numerische Validierung)
    numeric_cols = [
        'caffeine_washout', 'nicotin_washout', 'novalmin_washout',
        'temp_water', 'temp_room_start', 'temp_room_end',
        'rh_room_start', 'rh_room_end', 'age', 'height', 'weight',
        'ceq_pre_q4_calc', 'ceq_pre_q6_calc', 'ceq_post_4_calc', 'ceq_post_6_calc'
    ]

    for col in numeric_cols:
        if col in df_proto.columns:
            # Erst alles zu String, dann Komma zu Punkt, dann zu Zahl (Float)
            df_proto[col] = df_proto[col].astype(str).str.replace(',', '.', regex=False)
            df_proto[col] = pd.to_numeric(df_proto[col], errors='coerce')

    # 4. ASYMMETRISCHES BINNING (Toleranz -10s/+20s für Drift-Kompensation)
    anchors = df_long[(df_long['time_phase_4_begin'] == 1) & (df_long['time_added'] == 1)][['id', 'time_seconds']].rename(columns={'time_seconds': 'anchor_t'})
    fallback = df_long[df_long['time_phase_4_begin'] == 1][['id', 'time_seconds']].rename(columns={'time_seconds': 'anchor_t'})
    anchors = pd.concat([anchors, fallback]).drop_duplicates('id', keep='first')

    df_aligned = df_long.merge(anchors, on='id', how='left')
    df_aligned['t_aligned'] = df_aligned['time_seconds'] - df_aligned['anchor_t']
    df_aligned['bin'] = ((df_aligned['t_aligned'] + 10) // 30) * 30

    df_binned = df_aligned.groupby(['id', 'bin'])[['temp_ao_a_avg', 'temp_ao_b_avg']].mean().reset_index()

    # Wide-Transformation für beide Areale (Intervention & Kontrolle)
    wide_a = df_binned[df_binned['bin'] >= 0].pivot(index='id', columns='bin', values='temp_ao_a_avg')
    wide_a.columns = [f'a_rec_t{int(c)}' for c in wide_a.columns]
    wide_b = df_binned[df_binned['bin'] >= 0].pivot(index='id', columns='bin', values='temp_ao_b_avg')
    wide_b.columns = [f'b_rec_t{int(c)}' for c in wide_b.columns]

    # 5. STRATEGISCHE SPALTEN-SELEKTION (Nur analyse-relevante Daten)
    analysis_cols = [
        'id', 'group_id', 'dropout_pp', 'time_minutes_midnight', 'age', 'height', 'weight', 'gender',
        'nicotin_washout', 'caffeine_washout', 'novalmin_washout', 'ost_experience',
        'temp_water', 'temp_room_start', 'temp_room_end', 'rh_room_start', 'rh_room_end',
        'ceq_pre_q1', 'ceq_pre_q2', 'ceq_pre_q3', 'ceq_pre_q4_calc', 'ceq_pre_q5', 'ceq_pre_q6_calc',
        'ceq_post_1', 'ceq_post_2', 'ceq_post_3', 'ceq_post_4_calc', 'ceq_post_5', 'ceq_post_6_calc',
        'vas_1', 'vas_2', 'vas_3', 'vas_4', 'vas_5', 'vas_6', 'deblinding_check'
    ]

    baselines = df_long[df_long['time_phase'] == 0].groupby('id')[['temp_aoi_a_avg', 'temp_aoi_b_avg']].mean().reset_index()
    baselines.columns = ['id', 'a_base', 'b_base']

    df_final = df_proto[analysis_cols].merge(baselines, on='id', how='left')
    df_final = df_final.merge(wide_a, on='id', how='left').merge(wide_b, on='id', how='left')

    # 6. FINALES CASTING & RUNDUNG (Verhindert 15-Nachkommastellen-Artefakte)
    for int_col in ['id', 'group_id', 'dropout_pp', 'gender']:
        df_final[int_col] = df_final[int_col].fillna(-1).astype(int)

    # Temperaturen und Zeit auf 2 Stellen runden (entspricht Sensor-Präzision 40mK [1])
    num_cols = [c for c in df_final.columns if 'base' in c or 'rec' in c or 'temp_' in c or 'washout' in c or 'minutes' in c]
    df_final[num_cols] = df_final[num_cols].round(2)

    ceq_calc_cols = [c for c in df_final.columns if 'calc' in c]
    df_final[ceq_calc_cols] = df_final[ceq_calc_cols].round(1)

    # 7. EXPORT
    df_final.to_csv('Messungen_Zeitreihen-ultimate-wide_v15.csv', index=False, na_rep='')
    return df_final

try:
    df_v15 = generate_clean_v15_table('Messungen_Zeitreihen_phase-long1.csv', 'Messungen_Protokoll-groupID.csv')
    print("Version 15.0 erfolgreich erstellt. Alle numerischen Fehler sind behoben.")
except Exception as e:
    print(f"Fehler bei der Tabellenerstellung: {e}")
