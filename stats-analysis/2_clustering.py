import pandas as pd
import numpy as np
from scipy.cluster.hierarchy import dendrogram, linkage, fcluster
import matplotlib.pyplot as plt

# 1. Datentransfer: Laden der aus Calc exportierten CSV
try:
    df = pd.read_csv('delta_t_data.csv', sep=',', decimal='.')
except FileNotFoundError:
    print("Fehler: Datei 'delta_t_data.csv' nicht gefunden.")
    exit()

# Vorbereitung der Arrays
# IDs als Labels für das Dendrogramm
ids = df['id'].astype(str).values
# Delta_T als Feature-Matrix (Reshape notwendig für univariate Daten)
X = df['delta_T'].values.reshape(-1, 1)

# 2. Hierarchisches Clustering
# Methode 'ward' entspricht Ward.D2 (Minimierung der Varianz innerhalb der Cluster)
Z = linkage(X, method='ward', metric='euclidean')

# 3. Cluster-Zuteilung (Erzwingen von 2 Gruppen für Responder-Analyse)
df['cluster'] = fcluster(Z, 2, criterion='maxclust')

# 4. Visualisierung (Dendrogramm)
plt.figure(figsize=(10, 6))
dendrogram(
    Z,
    labels=ids,
    #leaf_rotation=90.,
    leaf_font_size=10.,
    color_threshold=0.5  # Schwellenwert zur visuellen Trennung der Äste
)

plt.title('Hierarchisches Clustering (Ward.D2) - Diskrimination per Temperatur')
plt.xlabel('Probanden-ID')
plt.ylabel('Euklidische Distanz')
plt.axhline(y=0.5, color='r', linestyle='--') # Trennlinie für 2 Cluster
plt.tight_layout()
#plt.show()
plt.savefig('1dendrogram_stufe1.png', dpi=300)

# 5. Deskriptive Statistik pro Cluster (Objektivierung der Responder)
print("\nStatistische Charakteristik der Cluster:")
stats = df.groupby('cluster')['delta_T'].agg(['mean', 'std', 'count']).round(4)
print(stats)

# Ausgabe der ID-Zuordnung für den Übertrag nach Calc
print("\nMathematische Cluster-Zuteilung pro ID:")
mapping = df[['id', 'cluster']].sort_values(by='id')
print(mapping.to_string(index=False))

# Optional: Export als CSV für den direkten Import in Calc
mapping.to_csv('cluster_mapping.csv', index=False)
