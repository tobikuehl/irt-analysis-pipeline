#!/usr/bin/env bash
# ==============================================================================
# FLARE-INHIBITION (SCHNELLER HARDWARE-TEST)
# ==============================================================================
# 2 Bilder, verkürzte Intervalle zum Prüfen der Koordinaten und Abläufe
# ==============================================================================

termux-wake-lock

# CONFIGURATION (Für den schnellen Test modifiziert)
X_CALIB1=667
Y_CALIB1=194
X_CALIB2=590
Y_CALIB2=321

X_SHUTTER=480
Y_SHUTTER=2034

INTERVALL=10       # Nur 10 Sekunden zwischen den Bildern
TOTAL_BILDER=2     # Exakt 2 Testbilder
CALIB_ZEIT=3
START_PUFFER=5     # Nur 5 Sekunden Puffer für den App-Start
TEST_COUNTDOWN=3   # 3 Sekunden "Akklimatisierung" statt 13 Minuten

# ABSOLUTE TERMUX-PFADE
HIK_DIR="/data/data/com.termux/files/home/storage/pictures/HIKMICRO Viewer"
STUDIE_BASE="/data/data/com.termux/files/home/storage/shared/FI/Messungen"
SOUND_BASE="/data/data/com.termux/files/home/storage/shared/FI/sounds"

SOUND_ALERT="${SOUND_BASE}/service-login.oga"
SOUND_SHUTTER="${SOUND_BASE}/camera-shutter-leise.oga"
SOUND_TAPE="${SOUND_BASE}/dialog-warning-auth.oga"

CLEAR="clear"
RESET="\033[0m"
BOLD="\033[1m"
GREEN="\033[32m"
YELLOW="\033[33m"
CYAN="\033[36m"
WHITE_BG="\033[47m\033[30m"

PLAY_SOUND() {
    [ -f "$1" ] && termux-media-player play "$1" >/dev/null 2>&1 &
}

draw_line() {
    local cols=$(tput cols 2>/dev/null || echo 40)
    [ "$cols" -gt 50 ] && cols=50
    printf "${CYAN}"
    printf '=%.0s' $(seq 1 "$cols")
    printf "${RESET}\n"
}

# ==============================================================================
# PHASE 1: ADB CHECK
# ==============================================================================
$CLEAR
draw_line
echo -e "${BOLD}${WHITE_BG}  ⚠️ RUNNING SYSTEM TEST MODE  ${RESET}"
draw_line
echo -e "\n  ${YELLOW}🔄 Prüfe ADB-Verbindung...${RESET}"

if adb devices | grep -q -w "device"; then
    echo -e "  ${GREEN}✅ ADB aktiv! Starte Sound-Check...${RESET}"
    PLAY_SOUND "$SOUND_ALERT"
    sleep 1
    PLAY_SOUND "$SOUND_SHUTTER"
    sleep 1
else
    echo -e "  ${RED}❌ ADB nicht verbunden! Bitte zuerst koppeln/verbinden.${RESET}"
    termux-wake-unlock
    exit 1
fi

mkdir -p "$HIK_DIR"

# ==============================================================================
# PHASE 2: TEST-ID
# ==============================================================================
PROBAND_ID="TEST"
PHONE_BACKUP_DIR="${STUDIE_BASE}/Proband_${PROBAND_ID}"
mkdir -p "$PHONE_BACKUP_DIR"
LOG_FILE="${HIK_DIR}/proband_${PROBAND_ID}_messung.log"

echo "=== SYSTEMTEST ===" > "$LOG_FILE"

# ==============================================================================
# PHASE 3: SHORT COUNTDOWN
# ==============================================================================
echo -e "\n  ${YELLOW}⏱️ Simuliere Akklimatisierung (${TEST_COUNTDOWN}s)...${RESET}"
for ((i=TEST_COUNTDOWN; i>0; i--)); do
    printf "\r  Start in: ${BOLD}${YELLOW}%d${RESET} " $i
    sleep 1
done
echo -e "\n"

# ==============================================================================
# PHASE 4: APP INITIALISIERUNG
# ==============================================================================
draw_line
echo -e "  ${GREEN}🚀 Starte App & setze Display-Timeout...${RESET}"
draw_line

# Display auf 30 Min einfrieren & App killen für Clean State
adb shell settings put system screen_off_timeout 1800000
adb shell am force-stop com.hikvision.thermalGoogle
sleep 1

# App starten
adb shell monkey -p com.hikvision.thermalGoogle -c android.intent.category.LAUNCHER 1 >/dev/null 2>&1
sleep $START_PUFFER

# ==============================================================================
# PHASE 5: LOOP (2 Bilder)
# ==============================================================================
for ((i=0; i<TOTAL_BILDER; i++))
do
    loop_start=$(date +%s)
    SEKUNDEN=$((i * INTERVALL))

    echo -e "  📸 Verarbeite Test-Bild $((i+1))/$TOTAL_BILDER (${SEKUNDEN}s)..."

    # NUC Kalibrierung
    adb shell input tap $X_CALIB1 $Y_CALIB1 >/dev/null 2>&1
    sleep 1
    adb shell input tap $X_CALIB2 $Y_CALIB2 >/dev/null 2>&1
    sleep $CALIB_ZEIT

    # Foto auslösen
    PLAY_SOUND "$SOUND_SHUTTER"
    adb shell input tap $X_SHUTTER $Y_SHUTTER >/dev/null 2>&1

    # Sound-Intervall im Test simulieren
    if [ $i -eq 0 ]; then
        PLAY_SOUND "$SOUND_ALERT" # Erster Sound-Test im Loop
    else
        PLAY_SOUND "$SOUND_TAPE"  # Zweiter Sound-Test im Loop
    fi

    # Warten falls noch ein Bild kommt
    if [ $i -lt $((TOTAL_BILDER - 1)) ]; then
        loop_end=$(date +%s)
        elapsed=$((loop_end - loop_start))
        remaining_sleep=$((INTERVALL - elapsed))
        [ $remaining_sleep -le 0 ] && remaining_sleep=1
        sleep $remaining_sleep
    fi
done

# ==============================================================================
# PHASE 6: POST-FLIGHT (Datenverschiebung & Aufräumen)
# ==============================================================================
echo -e "\n  💾 Bereinige Testdaten und verschiebe Bilder..."
sleep 2

# Bilder in den Probanden-Ordner verschieben
mv "${HIK_DIR}"/* "${PHONE_BACKUP_DIR}/" 2>/dev/null

# 🔄 Hikmicro-App schließen und Termux wieder in den Vordergrund holen
echo -e "  🛑 Schließe Kamera-App und kehre zu Termux zurück..."
adb shell am force-stop com.hikvision.thermalGoogle
sleep 1
adb shell monkey -p com.termux -c android.intent.category.LAUNCHER 1 >/dev/null 2>&1
sleep 1

# Display-Sperre wieder freigeben & Timeout auf 30 Sekunden zurücksetzen
adb shell settings put system screen_off_timeout 30000
termux-wake-unlock


draw_line
echo -e "  ${GREEN}✅ TEST ERFOLGREICH BEENDET!${RESET}"
echo -e "  Display-Timeout wurde wieder auf 30s gesetzt."
echo -e "  Bilder & Log liegen im Ordner: Proband_TEST"
draw_line
exit 0
