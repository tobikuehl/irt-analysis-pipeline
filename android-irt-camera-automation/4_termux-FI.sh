#!/usr/bin/env bash
# ==============================================================================
# FLARE-INHIBITION (PILOTSTUDIE)
# ==============================================================================
# Autor: Tobias Kühl
# System: Android (GrapheneOS) via Termux
# v 1.5
# ==============================================================================

# 1. Hintergrund-Modus erzwingen (Verhindert CPU-Standby)
termux-wake-lock

# CONFIGURATION (Display-Koordinaten und Intervalle)
X_CALIB1=667
Y_CALIB1=194
X_CALIB2=590
Y_CALIB2=321

X_SHUTTER=480
Y_SHUTTER=2034

INTERVALL=30
TOTAL_BILDER=33    # Baseline t0 bis t32 (16 Minuten Gesamtlaufzeit)
CALIB_ZEIT=3
START_PUFFER=30    # 30s Puffer für sicheren Kamera-Kaltstart
AKKLIMATISIERUNG_MINUTEN=0

# PFADE
HIK_DIR="/data/data/com.termux/files/home/storage/pictures/HIKMICRO Viewer"
STUDIE_BASE="/data/data/com.termux/files/home/storage/shared/FI/Messungen"
SOUND_BASE="/data/data/com.termux/files/home/storage/shared/FI/sounds"

SOUND_ALERT="${SOUND_BASE}/service-login.oga" # ding
SOUND_SHUTTER="${SOUND_BASE}/camera-shutter-leise.oga"

# TUI-DESIGN (optimiert für schmale Bildschirme)
CLEAR="clear"
RESET="\033[0m"
BOLD="\033[1m"
RED="\033[31m"
GREEN="\033[32m"
YELLOW="\033[33m"
CYAN="\033[36m"
WHITE_BG="\033[47m\033[30m"

PLAY_SOUND() {
    [ -f "$1" ] && termux-media-player play "$1" >/dev/null 2>&1 &
}

# Erzeugt eine Linie, die sich an die Displaybreite anpasst
draw_line() {
    local cols=$(tput cols 2>/dev/null || echo 40)
    [ "$cols" -gt 50 ] && cols=50
    printf "${CYAN}"
    printf '=%.0s' $(seq 1 "$cols")
    printf "${RESET}\n"
}

# ==============================================================================
# PHASE 1: PRE-FLIGHT CHECK & INTERAKTIVES ADB-PAIRING
# ==============================================================================
$CLEAR
draw_line
echo -e "${BOLD}${WHITE_BG}  PHASE 1: HARDWARE & ADB CHECK  ${RESET}"
draw_line
echo -e "\n  ${YELLOW}🔄 Prüfe lokale ADB-Verbindung...${RESET}"

# Prüfen, ob bereits ein Gerät verbunden ist
if adb devices | grep -q -w "device"; then
    echo -e "  ${GREEN}✅ ADB ist bereits verbunden!${RESET}"
else
    echo -e "  ${RED}❌ Keine aktive ADB-Verbindung gefunden.${RESET}"
    echo -e "\n  ${CYAN}ℹ️ Bitte in den Entwickleroptionen 'Wireless Debugging' öffnen.${RESET}"
    echo -e "  Wähle: ${BOLD}'Gerät mit Kopplungscode koppeln'${RESET}\n"

    # 1. Pairing (falls das Gerät in Termux noch nie gekoppelt wurde)
    echo -ne "  Muss das Gerät neu gekoppelt werden? (j/n): "
    read NEU_KOPPELN
    if [[ "$NEU_KOPPELN" == "j" || "$NEU_KOPPELN" == "J" ]]; then
        echo -ne "  👉 Bitte den 5-stelligen ${BOLD}Port${RESET} für die Kopplung eingeben: "
        read PAIR_PORT
        echo -ne "  👉 Bitte den 6-stelligen ${BOLD}WLAN-Kopplungscode${RESET} eingeben: "
        read PAIR_CODE
        echo -e "  ${YELLOW}Versuche Kopplung...${RESET}"
        adb pair localhost:$PAIR_PORT $PAIR_CODE
        echo -e "\n  ${CYAN}Kopplung abgeschlossen. Gehe nun im Menü einen Schritt zurück.${RESET}"
    fi

    # 2. Verbinden (benötigt den Verbindungs-Port, NICHT den Pairing-Port!)
    echo -e "\n  Schau nun unter 'IP-Adresse & Port' im Wireless Debugging Menü."
    echo -ne "  👉 Bitte den 5-stelligen ${BOLD}Verbindungs-Port${RESET} eingeben: "
    read CONN_PORT
    echo -e "  ${YELLOW}Stelle Verbindung her...${RESET}"
    adb connect localhost:$CONN_PORT

    # 3. Finaler Check
    sleep 2
    if adb devices | grep -q -w "device"; then
        echo -e "  ${GREEN}✅ ADB-Verbindung erfolgreich hergestellt!${RESET}"
        
        # Sound-Check mit Pausen für akustische Bestätigung
        echo -e "  ${YELLOW}🎵 Führe Sound-Check durch...${RESET}"
        PLAY_SOUND "$SOUND_ALERT"
        sleep 1
        PLAY_SOUND "$SOUND_SHUTTER"
        sleep 1
    else
        echo -e "\n  ${RED}${BOLD}❌ FEHLER: Verbindung fehlgeschlagen!${RESET}"
        echo -e "  ${RED}Bitte überprüfe die Ports und starte das Skript neu.${RESET}\n"
        draw_line
        termux-wake-unlock
        exit 1
    fi
fi

mkdir -p "$HIK_DIR"
sleep 1

# ==============================================================================
# PHASE 2: PROBANDEN-ID ERFASSEN (Vor der Akklimatisierung)
# ==============================================================================
$CLEAR
draw_line
echo -e "  ${BOLD}${YELLOW}📋 INITIALISIERUNG PROBANDEN-DATEN${RESET}"
draw_line
echo -e "\n  ${BOLD}Bitte Probanden-ID eingeben:${RESET}"
echo -ne "  ${CYAN}👉 ${RESET}"
read PROBAND_ID

if [ -z "$PROBAND_ID" ]; then
    echo -e "\n  ${RED}❌ Abbruch: Keine ID eingegeben.${RESET}"
    draw_line
    termux-wake-unlock
    exit 0
fi

PHONE_BACKUP_DIR="${STUDIE_BASE}/Proband_${PROBAND_ID}"
mkdir -p "$PHONE_BACKUP_DIR"
LOG_FILE="${HIK_DIR}/proband_${PROBAND_ID}_messung.log"

# Start des Protokolls schreiben
echo "=== MESSUNG PROBAND ${PROBAND_ID} (30s INTERVALL) ===" > "$LOG_FILE"
date "+%Y-%m-%d %H:%M:%S - Skript gestartet und ID registriert" >> "$LOG_FILE"

# ==============================================================================
# PHASE 3: AUTOMATISCHER MESSSTART
# ==============================================================================
$CLEAR
draw_line
echo -e "${BOLD}${GREEN}🔔 AKKLIMATISIERUNG BEENDET!${RESET}"
draw_line
echo -e "\n  🚀 Starte Hikmicro-App im Vordergrund..."
echo -e "  Baseline (Bild 0) beginnt in ${BOLD}${START_PUFFER} Sekunden${RESET}."
draw_line

# Bildschirm erzwungen eingeschaltet lassen und HikVision-App resetten
adb shell settings put system screen_off_timeout 1800000
adb shell am force-stop com.hikvision.thermalGoogle
sleep 2

# App sauber über den Paketnamen starten
adb shell monkey -p com.hikvision.thermalGoogle -c android.intent.category.LAUNCHER 1 >/dev/null 2>&1

# Puffer für Kamera-Kaltstart
sleep $START_PUFFER
STUDIE_START=$(date +%s)
date "+%Y-%m-%d %H:%M:%S - MESSREIHE GESTARTET (Bild 0 / 000s)" >> "$LOG_FILE"

# ==============================================================================
# PHASE 4: CORE MESS-SCHLEIFE (30s Taktung mit NUC-Vorlauf)
# ==============================================================================
for ((i=0; i<TOTAL_BILDER; i++))
do
    loop_start=$(date +%s)
    SEKUNDEN=$((i * INTERVALL))
    MSG=""

    # 1. KALIBRIERUNG (NUC) - 3 Sekunden vor dem Bild auslösen
    adb shell input tap $X_CALIB1 $Y_CALIB1 >/dev/null 2>&1
    sleep 1
    adb shell input tap $X_CALIB2 $Y_CALIB2 >/dev/null 2>&1
    date "+%Y-%m-%d %H:%M:%S - Bild $i (${SEKUNDEN}s): NUC-Kalibrierung gestartet" >> "$LOG_FILE"

    # Präzise Wartezeit für Sensorstabilisierung
    sleep $CALIB_ZEIT

    # 2. SNAPSHOT AUSLÖSEN
    PLAY_SOUND "$SOUND_SHUTTER"
    adb shell input tap $X_SHUTTER $Y_SHUTTER >/dev/null 2>&1
    date "+%Y-%m-%d %H:%M:%S - Bild $i (${SEKUNDEN}s): Snapshot ausgelöst" >> "$LOG_FILE"

    # 3. AKUSTISCHE TIMER-SIGNALE (VAS)
    case $SEKUNDEN in
        0)
            MSG="VAS 1 (Baseline)"
            PLAY_SOUND "$SOUND_ALERT"
            ;;
        45)
            MSG="VAS 2 + Abbruchcheck (Post-Reiz)"
            PLAY_SOUND "$SOUND_ALERT"
            ;;
        90)
            MSG="VAS 3"
            PLAY_SOUND "$SOUND_ALERT"
            ;;
        300)
            MSG="VAS 4 (HAUPT-ENDPUNKT)"
            PLAY_SOUND "$SOUND_ALERT"
            ;;
        600)
            MSG="VAS 5"
            PLAY_SOUND "$SOUND_ALERT"
            ;;
        930)
            MSG="VAS 6 (Finale Kinetik)"
            PLAY_SOUND "$SOUND_ALERT"
            ;;
    esac

    if [ ! -z "$MSG" ]; then
        date "+%Y-%m-%d %H:%M:%S - Bild $i (${SEKUNDEN}s): Akustischer Alarm für: $MSG" >> "$LOG_FILE"
    fi

    # 4. Warten bis zum nächsten 30-Sekunden-Fenster
    if [ $i -lt $((TOTAL_BILDER - 1)) ]; then
        loop_end=$(date +%s)
        elapsed=$((loop_end - loop_start))
        remaining_sleep=$((INTERVALL - elapsed))

        [ $remaining_sleep -le 0 ] && remaining_sleep=1
        sleep $remaining_sleep
    fi
done

date "+%Y-%m-%d %H:%M:%S - Messreihe erfolgreich beendet. 33 Bilder gesichert." >> "$LOG_FILE"

# ==============================================================================
# PHASE 6: POST-FLIGHT (Datenverschiebung & Aufräumen)
# ==============================================================================
echo -e "\n  💾 Verschiebe Bilder..."
sleep 3

# Bilder in den Probanden-Ordner verschieben
mv "${HIK_DIR}"/* "${PHONE_BACKUP_DIR}/" 2>/dev/null

# 🔄 Hikmicro-App schließen und Termux wieder in den Vordergrund holen
echo -e "  🛑 Schließe Kamera-App..."
adb shell am force-stop com.hikvision.thermalGoogle
sleep 1
adb shell monkey -p com.termux -c android.intent.category.LAUNCHER 1 >/dev/null 2>&1
sleep 1

# Display-Sperre wieder freigeben & Timeout auf 30 Sekunden zurücksetzen
adb shell settings put system screen_off_timeout 30000
termux-wake-unlock

echo -e "  ${GREEN}✅ Fertig! Daten liegen in: Proband_${PROBAND_ID}${RESET}\n"
exit 0
