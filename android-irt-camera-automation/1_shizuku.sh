#!/data/data/com.termux/files/usr/bin/bash
# Beispiel-Skript von irgendwo her...

echo "Suche aktiven Wireless-ADB Port..."
# Holt die lokale IP-Adresse des Geräts
LOCAL_IP="127.0.0.1"

# Durchsuche die typischen Android-Debug-Ports
for port in $(seq 37000 45000); do
    # Versuche im Hintergrund eine schnelle Verbindung
    (echo > /dev/tcp/$LOCAL_IP/$port) >/dev/null 2>&1
    if [ $? -eq 0 ]; then
        echo "Port gefunden: $port. Verbinde..."
        adb connect $LOCAL_IP:$port >/dev/null 2>&1

        # Shizuku Start-Befehl senden
        sh /sdcard/Android/data/moe.shizuku.privileged.api/start.sh
        echo "Shizuku-Startbefehl gesendet!"
        exit 0
    fi
done

echo "Fehler: Kein aktiver Port gefunden."
echo "Prüfe, ob 'Drahtloses Debugging' in den Android-Einstellungen aktiv ist!"
exit 0
