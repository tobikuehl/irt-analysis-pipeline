import pandas as pd
import numpy as np

def process_aligned_data(filename):
    # 1. DATEN LADEN
    df = pd.read_csv(filename, sep=',')
    df_proto = pd.read_csv('Messungen_Protokoll-groupID.csv', sep=',')

    # 2. NUMERISCHE INTEGRITÄT ERZWINGEN (Fehlerbehebung)
    # Wir bereinigen die Temperaturspalten von Kommata und wandeln sie in Floats um
    for col in ['temp_aoi_a_avg', 'temp_aoi_b_avg', 'time_seconds']:
        if df[col].dtype == 'object':
            df[col] = df[col].str.replace(',', '.')
        df[col] = pd.to_numeric(df[col], errors='coerce')

    # Per-Protocol Filter
    valid_ids = df_proto[df_proto['dropout_pp'] == 0]['id'].unique()
    df = df[df['id'].isin(valid_ids)].copy()

    # 3. ANKER-ZEITEN DEFINIEREN (Phase 4 Start)
    # Wir suchen den Zeitpunkt, an dem phase_4_begin markiert ist
    anchors = df[df['time_phase_4_begin'] == 1][['id', 'time_seconds']].rename(columns={'time_seconds': 'anchor_time'})

    # Fallback: Falls kein Anker gesetzt ist, nimm den ersten Phase-4-Eintrag
    fallback_anchors = df[df['time_phase'] == 4].groupby('id')['time_seconds'].min().reset_index().rename(columns={'time_seconds': 'anchor_time'})
    final_anchors = pd.merge(fallback_anchors, anchors, on='id', how='left')
    final_anchors['anchor_time'] = final_anchors['anchor_time_y'].fillna(final_anchors['anchor_time_x'])

    # 4. ZEITREIHEN AUSRICHTEN
    df = df.merge(final_anchors[['id', 'anchor_time']], on='id')
    df['time_aligned'] = df['time_seconds'] - df['anchor_time']

    # 5. BINNING (30s-Raster zur Glättung nach Shusterman)
    df['time_bin'] = (df['time_aligned'] / 30).round().astype(int) * 30

    # Hier passierte der Fehler: mean() braucht echte Zahlen
    df_binned = df.groupby(['id', 'time_bin'])[['temp_aoi_a_avg', 'temp_aoi_b_avg']].mean().reset_index()

    # 6. TRANSFORMATION INS WIDE-FORMAT (Recovery-Phase)
    df_recovery = df_binned[df_binned['time_bin'] >= 0]
    wide_a = df_recovery.pivot(index='id', columns='time_bin', values='temp_aoi_a_avg')
    wide_a.columns = [f'a_rec_t{int(c)}' for c in wide_a.columns]

    # 7. BASELINE (Mittelwert Phase 0) ALS REFERENZ
    baselines = df[df['time_phase'] == 0].groupby('id')['temp_aoi_a_avg'].mean().reset_index().rename(columns={'temp_aoi_a_avg': 'baseline_avg'})

    # 8. FINALER MERGE UND EXPORT
    df_wide = df_proto[['id', 'group_id']].merge(baselines, on='id').merge(wide_a, on='id')
    df_wide.to_csv('Messungen_Zeitreihen-final-wide.csv', index=False)

    return df_wide

try:
    df_final = process_aligned_data('Messungen_Zeitreihen_phase-long.csv')
    print("Alignment v5.9.0 erfolgreich. Fehler 'dtype str' wurde durch Konvertierung behoben.")
    # Kurze Kontrolle der ersten Zeilen
    print(df_final[['id', 'group_id', 'baseline_avg']].head())
except Exception as e:
    print(f"Fehler im Prozess: {e}")
