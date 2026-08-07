import pandas as pd

df = pd.read_csv('Messungen_Zeitreihen_phase-long1.csv')

# Check 1: Welche Phasen sind pro ID vorhanden?
print("--- Zeilenanzahl pro Phase ---")
print(df.groupby(['id', 'time_phase']).size().unstack(fill_value=0).head(10))

# Check 2: Gibt es leere IDs?
print("\nAnzahl NaN-Werte in der ID-Spalte:", df['id'].isna().sum())

# Check 3: Datentypen prüfen
print("\nDatentypen der Spalten:")
print(df.dtypes[['id', 'time_phase', 'temp_aoi_a_avg']])
