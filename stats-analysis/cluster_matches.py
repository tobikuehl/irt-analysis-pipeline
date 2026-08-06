"""
DATEI: C2_Clusteranalyse_und_Matchquote.py
BESCHREIBUNG:
Durchführung einer hierarchischen Clusteranalyse (Ward-Linkage) basierend
auf der AUC-Metrik zur Validierung der diskriminativen Trennschärfe.
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from scipy.cluster.hierarchy import dendrogram, linkage, fcluster

# 1. DATENLADUNG (Basiert auf bereinigten Daten aus Skript C1)
df = pd.read_csv('final_analyzed_data.csv') # Alternativ: Merge-Logik aus C1

# 2. HIERARCHISCHE CLUSTERANALYSE
# Feature-Vektor: AUC-Delta
X = df[['auc_delta']].values
Z = linkage(X, method='ward')

# 3. VISUALISIERUNG (DENDROGRAMM)
plt.figure(figsize=(10, 7))
dendrogram(Z, labels=df['id'].values, leaf_rotation=90)
plt.title('Hierarchisches Clustering der Entzündungsantwort (AUC)')
plt.xlabel('Probanden-ID')
plt.ylabel('Ward-Distanz')
plt.axhline(y=np.percentile(Z[:, 2], 90), color='r', linestyle='--') # Trennschwelle
plt.show()

# 4. VALIDIERUNG (Match-Quote)
# Aufteilung in zwei mathematische Cluster
df['cluster'] = fcluster(Z, 2, criterion='maxclust') - 1

# Da Cluster-IDs (0/1) nicht zwingend group_id (0/1) entsprechen:
# Berechnung der Match-Quote für beide Polaritäten
match_1 = (df['cluster'] == df['group_id']).mean()
match_2 = (df['cluster'] != df['group_id']).mean()
final_match_quote = max(match_1, match_2)

print(f"Analyse abgeschlossen.")
print(f"Mathematische Match-Quote zur klinischen Gruppierung: {final_match_quote*100:.2f} %")

