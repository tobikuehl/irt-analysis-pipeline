#!/usr/bin/env bash
# ==============================================================================
# FLARE-INHIBITION (PILOTSTUDIE)
# ==============================================================================
# Autor: M.Sc. Osteopathie Forschungsetup
# System: Android (GrapheneOS) via Termux (Flugmodus + Bluetooth)
# v 0.5
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
AKKLIMATISIERUNG_MINUTEN=13

# PFADE
HIK_DIR="/sdcard/Pictures/HIKMICRO Viewer"
STUDIE_BASE="/sdcard/FI/Messungen"
SOUND_BASE="/sdcard/FI/sounds"

SOUND_ALERT="${SOUND_BASE}/service-login.oga" # ding
SOUND_SHUTTER="${SOUND_BASE}/camera-shutter-leise.oga"
SOUND_TAPE="${SOUND_BASE}/dialog-warning-auth.oga" # Tok-Tok

# TUI DESIGN (Kontrastreich für kleine Bildschirme)
CLEAR="clear"
RESET="\e[0m"
BOLD="\e[1m"
RED="\e[31m"
GREEN="\e[32m"
YELLOW="\e[33m"
CYAN="\e[36m"
WHITE_BG="\e[47m\e[30m"

PLAY_SOUND() {
    [ -f "$1" ] && termux-media-player play "$1" >/dev/null 2>&1 &
}

draw_line() {
    echo -e "${CYAN}============================================================${RESET}";
}

# ==============================================================================
# PHASE 1: PRE-FLIGHT CHECK & INTERAKTIVES ADB-PAIRING
# ==============================================================================
$CLEAR
draw_line
echo -e "${BOLD}${WHITE_BG}         PHASE 1: HARDWARE & ADB VERBINDUNGS-CHECK          ${RESET}"
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

        # Sound-Check
        echo -e "  ${YELLOW}🎵 Führe Sound-Check durch...${RESET}"
        PLAY_SOUND "$SOUND_ALERT"
        sleep 1
        PLAY_SOUND "$SOUND_SHUTTER"
        sleep 1
        PLAY_SOUND "$SOUND_TAPE"
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
echo -e "\n  ${BOLD}Bitte Probanden-ID eingeben (z.B. 001):${RESET}"
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
# PHASE 3: AKKLIMATISIERUNG & AUFWÄRMZEIT (13 Minuten Countdown)
# ==============================================================================
$CLEAR
draw_line
echo -e "${BOLD}${WHITE_BG}       PHASE 3: AKKLIMATISIERUNG & CAMERA WARM-UP       ${RESET}"
draw_line
echo -e "  Probanden-ID: ${GREEN}${PROBAND_ID}${RESET}"
echo -e "\n  ${YELLOW}ℹ️  Führen Sie jetzt die Aufklärung und den Prä-Check durch.${RESET}\n"

TOTAL_SECS=$((AKKLIMATISIERUNG_MINUTEN * 60))
START_TIME=$(date +%s)

while [ $TOTAL_SECS -gt 0 ]; do
    MINS=$((TOTAL_SECS / 60))
    SECS=$((TOTAL_SECS % 60))
    printf "\r  ⏱️  Verbleibende Zeit: ${BOLD}${YELLOW}%02d:%02d${RESET} Min. " $MINS $SECS
    sleep 1
    CURRENT_TIME=$(date +%s)
    ELAPSED=$((CURRENT_TIME - START_TIME))
    TOTAL_SECS=$(( (AKKLIMATISIERUNG_MINUTEN * 60) - ELAPSED ))
done

# Signalton nach Ablauf der 13 Minuten
PLAY_SOUND "$SOUND_ALERT"
date "+%Y-%m-%d %H:%M:%S - 13 Minuten Akklimatisierung beendet" >> "$LOG_FILE"

# ==============================================================================
# PHASE 4: AUTOMATISCHER MESSSTART (Keine manuelle Eingabe mehr nötig!)
# ==============================================================================
$CLEAR
draw_line
echo -e "  ${BOLD}${GREEN}🔔 AKKLIMATISIERUNG BEENDET!${RESET}"
draw_line
echo -e "\n  🚀 Starte Hikmicro-App im Vordergrund..."
echo -e "  Die Baseline-Messung (Bild 0) beginnt in ${BOLD}${START_PUFFER} Sekunden${RESET}."
draw_line

# Bildschirm eingeschaltet lassen und HikVision-App schließen
adb shell svc power stayon true
adb shell am force-stop com.hikvision.thermalGoogle
sleep 2

# App starten oder über den exakten GrapheneOS-Paketnamen erzwingen
adb shell monkey -p com.hikvision.thermalGoogle -c android.intent.category.LAUNCHER 1 >/dev/null 2>&1

# 30 Sekunden Puffer für stabilen Kamera-Kaltstart (Vermeidet leere Bilder)
sleep $START_PUFFER
STUDIE_START=$(date +%s)
date "+%Y-%m-%d %H:%M:%S - MESSREIHE GESTARTET (Bild 0 / 000s)" >> "$LOG_FILE"

# ==============================================================================
# PHASE 5: CORE MESS-SCHLEIFE (Optimiert für NUC-Vorlauf vor dem Snapshot)
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

    # Präzise Wartezeit, damit der Sensor sich stabilisiert (Vorgabe: 3-4s)
    sleep $CALIB_ZEIT

    # 2. SNAPSHOT AUSLÖSEN (Direkt nach der Stabilisierung)
    PLAY_SOUND "$SOUND_SHUTTER"
    adb shell input tap $X_SHUTTER $Y_SHUTTER >/dev/null 2>&1
    date "+%Y-%m-%d %H:%M:%S - Bild $i (${SEKUNDEN}s): Snapshot ausgelöst" >> "$LOG_FILE"

    # 3. ZUSATZSOUNDS & ALARME (Erst NACH dem Bild, um Artefakte zu vermeiden)
    case $SEKUNDEN in
        0)
            MSG="VAS 1 (Baseline)"
            PLAY_SOUND "$SOUND_ALERT"
            ;;
        60)
            MSG="VAS 2 + Abbruchcheck (Post-Reiz)"
            PLAY_SOUND "$SOUND_ALERT"
            ;;
        180)
            MSG="VAS 3"
            PLAY_SOUND "$SOUND_ALERT"
            ;;
        240)
            MSG="VAS 4 (HAUPT-ENDPUNKT)"
            PLAY_SOUND "$SOUND_ALERT"
            ;;
        300)
            MSG="K-Tape nachfeuchten!"
            if [ -f "$SOUND_TAPE" ]; then
                PLAY_SOUND "$SOUND_TAPE"
            else
                PLAY_SOUND "$SOUND_ALERT"
                sleep 0.4
                PLAY_SOUND "$SOUND_ALERT"
            fi
            ;;
        540)
            MSG="VAS 5"
            PLAY_SOUND "$SOUND_ALERT"
            ;;
        960)
            MSG="VAS 6 (Finale Kinetik)"
            PLAY_SOUND "$SOUND_ALERT"
            ;;
    esac

    # Protokollierung des Alarms im Log-File (falls einer ausgelöst wurde)
    if [ ! -z "$MSG" ]; then
        date "+%Y-%m-%d %H:%M:%S - Bild $i (${SEKUNDEN}s): Akustischer Alarm für: $MSG" >> "$LOG_FILE"
    fi

    # 4. Präzises Warten bis zum nächsten äquidistanten 30-Sekunden-Fenster
    if [ $i -lt $((TOTAL_BILDER - 1)) ]; then
        loop_end=$(date +%s)
        elapsed=$((loop_end - loop_start))
        remaining_sleep=$((INTERVALL - elapsed))

        # Sicherheitsnetz: Falls ADB-Latenzen zu hoch werden
        [ $remaining_sleep -le 0 ] && remaining_sleep=1
        sleep $remaining_sleep
    fi
done

date "+%Y-%m-%d %H:%M:%S - Messreihe erfolgreich beendet. 33 Bilder gesichert." >> "$LOG_FILE"

# ==============================================================================
# PHASE 6: POST-FLIGHT (Automatische Datenverschiebung in Probanden-Zielordner)
# ==============================================================================
echo -e "\n  💾 Bereinige Messdaten und verschiebe Bilder..."

# Sicherheits-Puffer, damit das letzte Bild vollständig geschrieben ist
sleep 3

mv "${HIK_DIR}"/* "${PHONE_BACKUP_DIR}/" 2>/dev/null

# Reaktivierung des Android-Energiesparmodus
adb shell svc power stayon false
termux-wake-unlock
exit 0
