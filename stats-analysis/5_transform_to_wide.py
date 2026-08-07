import pandas as pd
import numpy as np

def generate_fixed_v14_table(long_file, proto_file):
    df_long = pd.read_csv(long_file)
    df_proto = pd.read_csv(proto_file)

    # 1. Asymmetrisches Binning (Konstante Logik wie v11-v13)
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

    # 2. Radikale numerische Bereinigung (Kommata-Fix)
    # Wir nehmen alle Spalten auf, die Dezimalzahlen enthalten könnten
    float_cols = [
        'caffeine_washout', 'nicotin_washout', 'novalmin_washout',
        'temp_water', 'temp_room_start', 'temp_room_end',
        'rh_room_start', 'rh_room_end',
        'ceq_pre_q4_calc', 'ceq_pre_q6_calc', 'ceq_post_4_calc', 'ceq_post_6_calc'
    ]

    for col in float_cols:
        if col in df_proto.columns:
            # Falls es als Text (object) eingelesen wurde, Komma durch Punkt ersetzen
            if df_proto[col].dtype == 'object':
                df_proto[col] = df_proto[col].str.replace(',', '.', regex=False)
            # Umwandlung in numerische Werte (NaN bleibt NaN)
            df_proto[col] = pd.to_numeric(df_proto[col], errors='coerce')

    # 3. Spalten-Selektion für die ITT-Analyse
    proto_selection = [
        'id', 'group_id', 'dropout_pp', 'time_start', 'age', 'height', 'weight', 'gender',
        'nicotin_washout', 'caffeine_washout', 'novalmin_washout', 'ost_experience',
        'temp_water', 'temp_room_start', 'temp_room_end', 'rh_room_start', 'rh_room_end',
        'ceq_pre_q1', 'ceq_pre_q2', 'ceq_pre_q3', 'ceq_pre_q4_calc', 'ceq_pre_q5', 'ceq_pre_q6_calc',
        'ceq_post_1', 'ceq_post_2', 'ceq_post_3', 'ceq_post_4_calc', 'ceq_post_5', 'ceq_post_6_calc',
        'vas_1', 'vas_2', 'vas_3', 'vas_4', 'vas_5', 'vas_6', 'deblinding_check'
    ]

    baselines = df_long[df_long['time_phase'] == 0].groupby('id')[['temp_aoi_a_avg', 'temp_aoi_b_avg']].mean().reset_index()
    baselines.columns = ['id', 'a_base', 'b_base']

    df_final = df_proto[proto_selection].merge(baselines, on='id', how='left')
    df_final = df_final.merge(wide_a, on='id', how='left').merge(wide_b, on='id', how='left')

    # 4. Finales Casting & Rundung
    # Identifikatoren als Integer (NaN wird zu -1)
    for int_col in ['id', 'group_id', 'dropout_pp', 'gender']:
        df_final[int_col] = df_final[int_col].fillna(-1).astype(int)

    # Temperaturen und Washout auf 2 Nachkommastellen runden
    num_cols = [c for c in df_final.columns if 'base' in c or 'rec' in c or 'temp_' in c or 'washout' in c]
    df_final[num_cols] = df_final[num_cols].round(2)
    # CEQ Scores auf 1 Stelle
    df_final[[c for c in df_final.columns if 'calc' in c]] = df_final[[c for c in df_final.columns if 'calc' in c]].round(1)

    df_final.to_csv('Messungen_Zeitreihen-ultimate-wide_v14.csv', index=False, na_rep='')
    return df_final

try:
    df_v14 = generate_fixed_v14_table('Messungen_Zeitreihen_phase-long1.csv', 'Messungen_Protokoll-groupID.csv')
    print("Version 14.0 erstellt. Kommata in 'caffeine_washout' und 'temp_water' wurden eliminiert.")
except Exception as e:
    print(f"Fehler: {e}")
