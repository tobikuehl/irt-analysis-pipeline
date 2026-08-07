import pandas as pd
import numpy as np

try:
    # 1. DATEN LADEN (US-Settings: Punkt als Dezimaltrenner)
    df_ts = pd.read_csv('Messungen_Zeitreihen.csv', sep=',')
    df_proto = pd.read_csv('Messungen_Protokoll-groupID.csv', sep=',')

    # Spaltennamen säubern
    df_ts.columns = df_ts.columns.str.strip()
    df_proto.columns = df_proto.columns.str.strip()

    # 2. PER-PROTOCOL FILTERING
    valid_ids = df_proto[df_proto['dropout_pp'] == 0]['id'].unique()
    df_ts = df_ts[df_ts['id'].isin(valid_ids)]

    # 3. BASELINE (Phase 0) - Mittelwert als stabiler Startpunkt
    # Wir berechnen den Mittelwert der Phase 0 pro AOI
    base_a = df_ts[df_ts['time_phase'] == 0].groupby('id')['temp_aoi_a_avg'].mean().reset_index()
    base_b = df_ts[df_ts['time_phase'] == 0].groupby('id')['temp_aoi_b_avg'].mean().reset_index()

    base_df = base_a.merge(base_b, on='id', suffixes=('_base_a', '_base_b'))

    # 4. TRANSFORMATION DER POST-INTERVENTION (Phase 4) & ARTEFAKTE (Phase 3)
    # Wir behalten Phase 3 bei, markieren sie aber als NaN, um die Zeitreihen-Lücken
    # für JASP korrekt abzubilden (Missing Values statt Zeit-Stauchung).
    df_kinetics = df_ts[df_ts['time_phase'].isin([3, 4])].copy()

    # Falls Phase 3: Werte auf NaN setzen (da Bewegungsartefakte unbrauchbar sind)
    mask_art = df_kinetics['time_phase'] == 3
    df_kinetics.loc[mask_art, ['temp_aoi_a_avg', 'temp_aoi_b_avg']] = np.nan

    # 5. ZEITREIHEN-STABILE SPALTEN (Sequence-based mit Zeit-Info)
    # Da die Sekunden-Stempel variieren, nutzen wir die image_seq (relativ zum Start)
    # Wir pivotieren getrennt für AOI A und B

    # Pivot AOI A
    wide_a = df_kinetics.pivot(index='id', columns='image_seq', values='temp_aoi_a_avg')
    wide_a.columns = [f'a_seq{int(c)}' for c in wide_a.columns]

    # Pivot AOI B (Kontrolle)
    wide_b = df_kinetics.pivot(index='id', columns='image_seq', values='temp_aoi_b_avg')
    wide_b.columns = [f'b_seq{int(c)}' for c in wide_b.columns]

    # 6. MERGE ZUM FINALEN WIDE-FORMAT
    df_wide = df_proto[['id', 'group_id']].merge(base_df, on='id')
    df_wide = df_wide.merge(wide_a, on='id').merge(wide_b, on='id')

    # 7. EXPORT (Punkt-Dezimal für JASP)
    df_wide.to_csv('Messungen_Zeitreihen-wide.csv', index=False)

    print("\n--- Wide-Format Konvertierung v5.5.0 abgeschlossen ---")
    print(f"Dateiname: Messungen_Zeitreihen-wide.csv")
    print(f"Anzahl Probanden (PP): {len(df_wide)}")
    print(f"Zeitachse: Phase 3 (Artefakte) wurde als 'NaN' erhalten.")
    print(f"Kontroll-AOI: temp_aoi_b ist integriert.")

except Exception as e:
    print(f"Fehler: {e}")
