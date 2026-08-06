import pandas as pd
import numpy as np

# 1. Daten laden (Anpassung an deutsches Format falls nötig, sonst Standard)
try:
    # Versuche Standard-CSV, falls Fehler (z.B. Komma als Dezimal), nutze deutsches Format
    try:
        df = pd.read_csv('cohens_d.csv')
    except:
        df = pd.read_csv('cohens_d.csv', sep=';', decimal=',')

    # Gruppen trennen (1 = Verum, 0 = Sham)
    verum = df[df['group_id'] == 1]['auc_delta']
    sham = df[df['group_id'] == 0]['auc_delta']

    # 2. Deskriptive Statistik
    stats = df.groupby('group_id')['auc_delta'].agg(['mean', 'std', 'count'])
    print("\n--- Deskriptive Statistik pro Gruppe ---")
    print(stats)

    # 3. Cohen's d Berechnung
    n1, n2 = len(verum), len(sham)
    v1, v2 = verum.var(), sham.var()

    # Gepoolte Standardabweichung
    pooled_sd = np.sqrt(((n1 - 1) * v1 + (n2 - 1) * v2) / (n1 + n2 - 2))

    # Cohen's d (Mittelwertsdifferenz / gepoolte SD)
    d = (verum.mean() - sham.mean()) / pooled_sd

    print("\n--- Biometrische Kennwerte ---")
    print(f"Gepoolte Standardabweichung: {pooled_sd:.4f}")
    print(f"Effektstärke Cohen's d:      {d:.4f}")

except FileNotFoundError:
    print("Fehler: 'cohens_d.csv' nicht gefunden. Prüfe den Dateinamen.")
