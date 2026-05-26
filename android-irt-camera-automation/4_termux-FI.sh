#!/bin/bash
# v 0.2

# ==============================================================================
# KONFIGURATION (Werte aus dem Test-Skript hier eintragen)
# ==============================================================================
X_CALIB=500
Y_CALIB=1200
X_SHUTTER=960
Y_SHUTTER=2100

INTERVALL=30
BILDER=32
CALIB_ZEIT=3
TARGET_BASE_DIR="$HOME/Thermograhie_Studie"

# Sounddateien aus dem KDE6-Ocean-Theme (Beruhigendere Klänge)
SOUND_ALERT="/usr/share/sounds/ocean/stereo/dialog-information.oga"
SOUND_SHUTTER="/usr/share/sounds/ocean/stereo/camera-shutter.oga"

# ==============================================================================
# TUI FARBEN & DESIGN
# ==============================================================================
CLEAR="clear"
RESET="\e[0m"
BOLD="\e[1m"
RED="\e[31m"
GREEN="\e[32m"
YELLOW="\e[33m"
BLUE="\e[34m"
CYAN="\e[36m"
WHITE_BG="\e[47m\e[30m"

# Sound-Wiedergabefunktion mit Lautstärke-Dämpfung auf 40% für angenehme Raumatmosphäre
PLAY_SOUND() {
    local FILE=$1
    if command -v paplay &> /dev/null && [ -f "$FILE" ]; then
        paplay --volume=26214 "$FILE" >/dev/null 2>&1 &
    elif command -v pw-play &> /dev/null && [ -f "$FILE" ]; then
        pw-play --volume=0.8 "$FILE" >/dev/null 2>&1 &
    fi
}

draw_line() { echo -e "${CYAN}------------------------------------------------------------${RESET}"; }

# ==============================================================================
# TUI: DRAHTLOS-ADB VERBINDUNG PRÜFEN
# ==============================================================================
$CLEAR
echo -e "${BOLD}${CYAN}  ============================================================${RESET}"
echo -e "${BOLD}${WHITE_BG}         FLARE-INHIBITION - eine Pilotstudie         ${RESET}"
echo -e "${BOLD}${CYAN}  ============================================================${RESET}"
echo -e ""
echo -e "${YELLOW}  👉 Warte auf Drahtloses Debugging (max. 30s)...${RESET}"

if ! timeout 30 adb wait-for-device; then
    echo -e "${RED}  ❌ FEHLER: Timeout. Gerät nicht im WLAN gefunden.${RESET}"
    exit 1
fi
echo -e "${GREEN}  ✅ Kabellose ADB-Verbindung erfolgreich hergestellt!${RESET}"
sleep 1

# ==============================================================================
# VORAB-CHECK: DCIM BEREINIGEN
# ==============================================================================
DCIM_CONTENT=$(adb shell "ls -A /sdcard/DCIM/" 2>/dev/null | tr -d '\r')
if [ ! -z "$DCIM_CONTENT" ]; then
    TIMESTAMP=$(date +%Y%m%d_%H%M%S)
    adb shell "mkdir -p /sdcard/Thermo_Backup/NotfallBackup_${TIMESTAMP} && mv /sdcard/DCIM/* /sdcard/Thermo_Backup/NotfallBackup_${TIMESTAMP}/" 2>/dev/null
fi

# ==============================================================================
# PROBANDEN-DATEN EINGEBEN
# ==============================================================================
$CLEAR
draw_line
echo -e "${BOLD}${YELLOW}  📋 DATENERFASSUNG PROBAND${RESET}"
draw_line
echo ""
read -p "$(echo -e "${BOLD}  Bitte Probanden-ID eingeben: ${RESET}")" PROBAND_ID

if [ -z "$PROBAND_ID" ]; then
    echo -e "${RED}  Abbruch: Keine ID eingegeben.${RESET}"
    exit 0
fi

PHONE_BACKUP_DIR="/sdcard/Thermo_Backup/Proband_${PROBAND_ID}"
SURFACE_TARGET_DIR="${TARGET_BASE_DIR}/Proband_${PROBAND_ID}"

echo ""
echo -e "  📁 Zielpfad Pixel:   ${CYAN}${PHONE_BACKUP_DIR}${RESET}"
echo -e "  📁 Zielpfad Surface: ${CYAN}${SURFACE_TARGET_DIR}${RESET}"
echo ""
draw_line
read -p "$(echo -e "${BOLD}${GREEN}  👉 Drücke [ENTER] um die 16-Minuten-Messreihe zu STARTEN...${RESET}")"

# ==============================================================================
# CORE MESS-SCHLEIFE
# ==============================================================================
start_time=$(date +%s)

for ((i=1; i<=BILDER; i++))
do
    loop_start=$(date +%s)
    ACTION_MSG=""
    ACTION_ALERT=0

    case $i in
        1|3|7|9|18|32)
            ACTION_MSG="${RED}${BOLD}  ⚠️  AUFFORDERUNG: VAS 📝${RESET}"
            ACTION_ALERT=1
            ;;
        10)
            ACTION_MSG="${YELLOW}${BOLD}  💧 AKTION: SCHABLONE NEU ANFEUCHTEN 💧${RESET}"
            ACTION_ALERT=1
            ;;
    esac

    # Signalton aus dem Ocean-Theme abspielen bei fälliger Aktion
    if [ $ACTION_ALERT -eq 1 ]; then
        PLAY_SOUND "$SOUND_ALERT"
    fi

    # TUI Refresh
    $CLEAR
    draw_line
    echo -e "${BOLD}${WHITE_BG}          MESSREIHE LÄUFT: PROBAND ${PROBAND_ID}          ${RESET}"
    draw_line

    PROG_PERCENT=$(( (i * 100) / BILDER ))
    BAR_FILLED=$(( i / 2 ))
    BAR_EMPTY=$(( (BILDER - i) / 2 ))

    echo -e "\n${BOLD}  Gesamtfortschritt: [${GREEN}$(printf '#%.0s' $(seq 1 $BAR_FILLED))$(printf ' %.0s' $(seq 1 $BAR_EMPTY))${RESET}] ${PROG_PERCENT}%"
    echo -e "  Aktuelles Bild:     ${BOLD}${GREEN}$i${RESET} von ${BOLD}$BILDER${RESET}"
    echo -e "  Zeit seit Start:    ${CYAN}$(( (loop_start - start_time) )) Sek.${RESET}\n"

    if [ ! -z "$ACTION_MSG" ]; then
        echo -e "${CYAN}┌──────────────────────────────────────────────────────────┐${RESET}"
        echo -e "  $ACTION_MSG"
        echo -e "${CYAN}└──────────────────────────────────────────────────────────┘${RESET}\n"
    else
        echo -e "${BLUE}  ℹ️  Aktuell keine manuellen Probanden-Aktionen fällig.${RESET}\n"
    fi
    draw_line

    # 1. Kalibrierung auslösen
    echo -e "  🤖 Skript-Status: Triggere manuelle Kalibrierung (NUC)..."
    adb shell input tap $X_CALIB $Y_CALIB >/dev/null 2>&1
    sleep $CALIB_ZEIT

    # 2. Foto auslösen & Shutter-Sound abspielen
    echo -e "  📸 Skript-Status: Schieße Wärmebild..."
    PLAY_SOUND "$SOUND_SHUTTER"
    adb shell input tap $X_SHUTTER $Y_SHUTTER >/dev/null 2>&1

    # 3. Countdown bis zum nächsten Intervall
    if [ $i -lt $BILDER ]; then
        loop_end=$(date +%s)
        elapsed=$((loop_end - loop_start))
        remaining_sleep=$((INTERVALL - elapsed))
        if [ $remaining_sleep -le 0 ]; then remaining_sleep=1; fi # Schutzwert

        while [ $remaining_sleep -gt 0 ]
        do
            echo -ne "  ⏱️  Nächstes Intervall in: ${BOLD}${YELLOW}${remaining_sleep}s${RESET}   \r"
            sleep 1
            remaining_sleep=$((remaining_sleep - 1))
        done
    fi
done

# ==============================================================================
# SMARTPHONE AUTO-BACKUP
# ==============================================================================
$CLEAR
draw_line
echo -e "${BOLD}${GREEN}  ✅ MESSREIHE BEENDET! ALLE BILDER ERFOLGREICH IM KASTEN.${RESET}"
draw_line
echo -e "\n  Verschiebe Daten in den Probanden-Backup-Ordner auf dem Smartphone..."

adb shell "mkdir -p ${PHONE_BACKUP_DIR} && mv /sdcard/DCIM/* ${PHONE_BACKUP_DIR}/" 2>/dev/null
echo -e "  -> Datensicherung auf dem Pixel abgeschlossen: ${CYAN}${PHONE_BACKUP_DIR}${RESET}\n"
draw_line

# ==============================================================================
# DOWNLOAD AUF DAS SURFACE & GWENVIEW-AUFRUF
# ==============================================================================
echo -e "${BOLD}  Möchtest du die 32 Bilder jetzt kabellos herunterladen?${RESET}"
echo -e "  1) ${GREEN}Ja, jetzt via WLAN herunterladen${RESET}"
echo -e "  2) Nein, Daten vorerst auf dem Pixel belassen"
echo ""
read -p "  Auswahl (1 oder 2): " DOWNLOAD_CHOICE

if [ "$DOWNLOAD_CHOICE" = "1" ]; then
    mkdir -p "$SURFACE_TARGET_DIR"
    echo -e "\n  🔄 Übertragungs-Status: Ziehe Bilddaten via WLAN..."

    adb pull "${PHONE_BACKUP_DIR}/" "$TARGET_BASE_DIR/"

    if [ $? -eq 0 ]; then
        echo -e "\n${BOLD}${GREEN}  🎉 WIRELESS-DOWNLOAD ERFOLGREICH!${RESET}"
        echo -e "  Die Daten stehen zur Analyse bereit unter: ${CYAN}${SURFACE_TARGET_DIR}${RESET}\n"
        draw_line

        # GWENVIEW
        echo -e "${BOLD}  Möchten Sie die Bilder jetzt direkt in Gwenview zur Sichtung öffnen?${RESET}"
        echo -e "  1) ${GREEN}Ja, Gwenview starten${RESET}"
        echo -e "  2) Nein, nur das Skript beenden"
        echo ""
        read -p "  Auswahl (1 oder 2): " VIEW_CHOICE

        if [ "$VIEW_CHOICE" = "1" ]; then
            echo -e "\n  🚀 Starte Gwenview..."
            gwenview "$SURFACE_TARGET_DIR" >/dev/null 2>&1 &
        else
            echo -e "\n  ℹ️  Skript wird beendet. Sie können die Bilder später manuell sichten."
        fi
    else
        echo -e "\n${RED}  ❌ FEHLER beim WLAN-Download. Bitte prüfen Sie das Drahtlos-ADB-Netzwerk.${RESET}"
    fi
else
    echo -e "\n${YELLOW}  ℹ️  Vorgang beendet. Bilder liegen exklusiv im Smartphone-Speicher.${RESET}\n"
fi

draw_line
exit 0
