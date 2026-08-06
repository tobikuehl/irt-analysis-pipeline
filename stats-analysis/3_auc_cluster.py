import pandas as pd
import numpy as np
from scipy.cluster.hierarchy import dendrogram, linkage, fcluster
from scipy.integrate import trapezoid  # Neuer Import für die Integration
import matplotlib.pyplot as plt

# 1. Daten laden mit explizitem Datumsformat
try:
    df_raw = pd.read_csv(
        'Messungen_zeitreihen.csv',
        sep=',',
        decimal=',',
        quotechar='"',
        parse_dates=['timestamp'],
        date_format='%y-%m-%d %H:%M:%S' # Verhindert das UserWarning
    )
except Exception as e:
    print(f"Fehler beim Laden der Datei: {e}")
    exit()

def calculate_auc_and_cluster(df, phase4_limit=25):
    results = []
    # Per-Protocol Filterung: IDs mit Baseline (Phase 0) [1]
    pp_ids = df[df['time_phase'] == 0]['id'].unique()
    pp_ids = [id for id in pp_ids if id != 14] # Nikotin-Dropout [2]

    for subj_id in pp_ids:
        subj_data = df[df['id'] == subj_id].copy()

        # Phase 3 Maskierung [3]
        subj_data = subj_data[subj_data['time_phase'] != 3]

        base_temp = subj_data[subj_data['time_phase'] == 0]['temp_aoi_a_avg'].mean()

        p1_start = subj_data[subj_data['time_phase'] == 1].iloc[0:1]
        p4_data = subj_data[subj_data['time_phase'] == 4].iloc[:phase4_limit]

        if p1_start.empty or p4_data.empty:
            continue

        auc_data = pd.concat([p1_start, p4_data])
        t_start = p1_start['time_seconds'].values
        x = auc_data['time_seconds'].values - t_start
        y = auc_data['temp_aoi_a_avg'].values - base_temp

        # Trapezregel zur AUC-Berechnung (jetzt via scipy)
        auc_val = trapezoid(y, x)
        results.append({'id': subj_id, 'auc_delta': round(auc_val, 4)})

    df_auc = pd.DataFrame(results)

    # 2. Hierarchisches Clustering (Ward.D2) [4]
    X = df_auc['auc_delta'].values.reshape(-1, 1)
    Z = linkage(X, method='ward', metric='euclidean')
    df_auc['cluster'] = fcluster(Z, 2, criterion='maxclust')

    return df_auc, Z

# Ausführung
df_final, linkage_matrix = calculate_auc_and_cluster(df_raw)

# Ergebnisausgabe
print(f"\nAnalysiertes PP-Kollektiv: n = {len(df_final)}")
print(df_final.to_string(index=False))

# Dendrogramm speichern
plt.figure(figsize=(12, 7))
dendrogram(linkage_matrix, labels=df_final['id'].values.astype(str))
plt.title('Clustering (AUC der neurogenen Entzündung)')
plt.xlabel('Probanden-ID')
plt.ylabel('Euklidische Distanz')
plt.savefig('2dendrogram_auc_final.png', dpi=300)

# Deskriptive Statistik
stats = df_final.groupby('cluster')['auc_delta'].agg(['mean', 'std', 'count']).round(2)
print("\nStatistische Struktur der AUC-Cluster:")
print(stats)
