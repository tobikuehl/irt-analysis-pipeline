# IRT-Messdaten-Pipeline (Masterarbeit Osteopathie)
Automatisierte Datenaufbereitung, Zeitreihen-Transformation und statistische Auswertung von über **1.100 Seiten Infrarot-Thermografie-Reports aus 34 Messreihen (über 7.800 Einzelwerte)** im Rahmen meiner Masterarbeit (M.Sc. Osteopathie).

## Kontext & Hinweis zur Reproduzierbarkeit
Dieses Repository dokumentiert die im Rahmen der Masterarbeit entwickelte Python-Pipeline.

+ **Datenschutz:**  
  Die zugrunde liegenden CSV-Rohdaten und ODT-Reports enthalten physiologische Messreihen der Studienteilnehmenden und sind aus Gründen des Datenschutzes (Art. 9 DSGVO / Zweckbindung der Studieneinwilligung) nicht im Repository enthalten.
+ **Struktur (Exploration vs. Konsolidierung):**  
  Der Ordner `stats-analysis` enthält die nummerierten ursprünglichen Arbeitsskripte inklusive ihrer iterativen Entwicklungs- und Debugging-Historie (`git log`). Dort liegen auch die nachträglich bereinigten Skripte (ohne Nummerierung) zur dokumentierten Nachvollziehbarkeit der Berechnungsmethoden.

## Repository-Struktur
### 1. Automatisierung der Android-HIKMICRO-App (`android-irt-camera-automation`)
+ **`1_shizuku.sh`**: ein Test-Skript für die Automatisierung von Shizuku.
+ **`2_termux-setup.sh`**: ein Skript für die Testung der Koordinaten der NUC- und Auslöse-Buttons der HIKMICRO-App
+ **`3_termux-test.sh`**: ein Skript für einen Testlauf des Setups
+ **`4_termux-FI.sh`**: das Skript für die Durchführung der Mess-Reihen
  - **`/audio`**: enthält Audio-Dateien für die Rückmeldung des zeitlichen Verlaufs
+ **`Pre-flight.md`**: enthält Bemerkungen zu Tests und  erstem Ablauf

### 2. Explorative Pipeline (`stats-analysis`)
+ **`01_extractor.py`**: Extraktion der Daten aus den odt-Reports der Software Hikmicro Analyzer.
+ **`02_clustering.py`**: Initiales Ward-Clustering auf Basis der Delta-Werte und Erstellung des Cluster-Mappings.
+ **`03_auc_cluster.py`**: Filterung nach Studienprotokoll, Berechnung der relativen Area Under the Curve (AUC) mittels Trapezregel sowie hierarchisches Clustering (Ward-Methode) inklusive Dendrogramm-Export.
+ **`04_cohens_rmse.py`** *(7 Iterationen)*: Schrittweise Berechnung von Standardabweichung (SD), Effektstärke (Cohen's *d*), Baseline-Extraktion und Root Mean Square Error (RMSE).
+ **`05_transform_to_wide.py`** *(13 Iterationen)* **& `5_diagnostic-5.2-to-5.3.py`**: Dezimal-Normalisierung, Filterung, Baseline-Berechnung, Phasen-Einteilung, Handling fehlender Werte (Missing Data), Pivotierung vom Long- ins Wide-Format sowie Zeitpunkt-Berechnung und asymmetrisches Binning / Drift-Korrektur.
+ **`cluster_matches.py`**: Bereinigtes Skript für die Ward-Clusteranalyse auf Basis des AUC-Deltas.
+ **`data_preparation_auc.py`**: Bereinigte Berechnung von Dezimal-Normalisierung, Delta, RMSE und Cohen's *d* (AUC).

### 3. Studie (`pilot`)
+ **`README.md`**: Modulation of neurogenic inflammation following a controlled thermal stimulus—a randomized, sham-controlled, single-blind pilot study of a novel osteopathic approach (Vorgelegte Studie, alle Rechte vorbehalten).
+ **[kolloquium-feasibility-study.pdf](pilot/kolloquium-feasibility-study.pdf):** Gekürzte Kolloquiumspräsentation zum Studiendesign, Mess-Setup und zur statistischen Methodik (ohne unveröffentlichte Studienergebnisse).
