import pandas as pd
import numpy as np

def sanitize_ultimate_data(long_file, proto_file):
    # 1. DATENIMPORT
    df = pd.read_csv(long_file)
    df_proto = pd.read_csv(proto_file)

    # 2. PER-PROTOCOL FILTERUNG (n=25)
    valid_ids = df_proto[df_proto['dropout_pp'] == 0]['id'].unique()
    df = df[df['id'].isin(valid_ids)].copy()

    # 3. ANKER-ALIGNMENT & BINNING (wie v9.0)
    anchors = df[df['time_phase_4_begin'] == 1][['id', 'time_seconds']].rename(columns={'time_seconds': 'anchor_t'})
    df = df.merge(anchors, on='id', how='left')
    df['t_aligned'] = df['time_seconds'] - df['anchor_t']
    df['bin'] = (df['t_aligned'] / 30).round().astype(int) * 30
    df_binned = df.groupby(['id', 'bin'])[['temp_aoi_a_avg', 'temp_aoi_b_avg']].mean().reset_index()

    # 4. WIDE-FORMAT ERZEUGEN
    df_rec = df_binned[df_binned['bin'] >= 0]
    wide_a = df_rec.pivot(index='id', columns='bin', values='temp_aoi_a_avg')
    wide_a.columns = [f'a_rec_t{int(c)}' for c in wide_a.columns]
    wide_b = df_rec.pivot(index='id', columns='bin', values='temp_aoi_b_avg')
    wide_b.columns = [f'b_rec_t{int(c)}' for c in wide_b.columns]

    # 5. PROTOKOLL-DATEN AUFBEREITEN (Hardcore-Cleaning)
    # Spalten mit Kommata (Strings) in Floats wandeln
    for col in ['temp_water', 'temp_room_start', 'rh_room_start']:
        if df_proto[col].dtype == 'object':
            df_proto[col] = df_proto[col].str.replace(',', '.').astype(float)

    # CEQ-Scores runden (1 Nachkommastelle)
    ceq_cols = [c for c in df_proto.columns if 'calc' in c]
    df_proto[ceq_cols] = df_proto[ceq_cols].round(1)

    # 6. MERGE ZUR ULTIMATIVE-WIDE
    relevant_proto_cols = [
        'id', 'group_id', 'age', 'height', 'weight', 'gender',
        'nicotin_washout', 'caffeine_washout', 'novalmin_washout',
        'ost_experience', 'contraception', 'cycle_days', 'cycle_phase',
        'temp_water', 'temp_room_start', 'rh_room_start'
    ]

    # Baseline-Mittelwerte
    baselines = df[df['time_phase'] == 0].groupby('id')[['temp_aoi_a_avg', 'temp_aoi_b_avg']].mean().reset_index()
    baselines.columns = ['id', 'a_base', 'b_base']

    df_jasp = df_proto[relevant_proto_cols].merge(baselines, on='id', how='inner')
    df_jasp = df_jasp.merge(wide_a, on='id', how='inner').merge(wide_b, on='id', how='inner')

    # 7. FINALES TYP-CASTING (Integer erzwingen für JASP-Nominal-Skalen)
    # Wir füllen NaNs temporär mit -1, um Integer-Cast zu erlauben,
    # JASP erkennt -1 dann als eigene Kategorie oder wir lassen es als Float und definieren es in JASP.
    # Bessere Lösung für CSV: Wir runden einfach und lassen Pandas die .0 anhängen.

    # Temperaturen auf 2 Nachkommastellen (Präzision IRT)
    temp_cols = [c for c in df_jasp.columns if 'base' in c or 'rec' in c or 'temp_' in c]
    df_jasp[temp_cols] = df_jasp[temp_cols].round(2)

    # 8. EXPORT
    df_jasp.to_csv('Messungen_Zeitreihen-ultimate-wide_v10.csv', index=False, na_rep='')
    return df_jasp

try:
    df_final = sanitize_ultimate_data('Messungen_Zeitreihen_phase-long1.csv', 'Messungen_Protokoll-groupID.csv')
    print("Clean-Data-Package v10.0 erstellt. Alle Formate sind nun JASP-optimiert.")
except Exception as e:
    print(f"Kritischer Fehler beim Sanitizing: {e}")
