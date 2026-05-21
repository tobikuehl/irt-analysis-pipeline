#!/bin/bash
CLEAR="clear"
RESET="\e[0m"
BOLD="\e[1m"
CYAN="\e[36m"
YELLOW="\e[33m"
GREEN="\e[32m"

$CLEAR
echo -e "${BOLD}${CYAN}  ============================================================${RESET}"
echo -e "${BOLD}        ANLEITUNG: KOORDINATEN FÜR SCRCPY ERMITTELN           ${RESET}"
echo -e "${BOLD}${CYAN}  ============================================================${RESET}"
echo -e ""
echo -e "${BOLD}  1. Vorbereitung auf dem Pixel 9 Pro:${RESET}"
echo -e "     - Gehe in die ${YELLOW}Einstellungen -> Entwickleroptionen${RESET}."
echo -e "     - Aktiviere den Punkt ${YELLOW}'Zeigerposition anzeigen'${RESET}."
echo -e "     - Oben auf dem Smartphone-Display erscheint nun eine graue Leiste."
echo -e ""
echo -e "${BOLD}  2. Koordinaten ablesen via scrcpy:${RESET}"
echo -e "     - Starte die HIKMICRO-App auf dem Pixel."
echo -e "     - Tippe (im scrcpy-Fenster) auf den ${GREEN}Kalibrierungs-Button${RESET}."
echo -e "     - Lies ganz oben in der grauen Leiste den ${BOLD}X:${RESET}- und ${BOLD}Y:${RESET}-Wert ab."
echo -e "     - Wiederhole das für den ${GREEN}Foto-Auslöser-Button${RESET}."
echo -e ""
echo -e "${BOLD}  3. Für die Analyse:${RESET}"
echo -e "     - Lade  ${YELLOW}Windows (Tiny11)${RESET}  von:"
echo -e "         * -> ${YELLOW}https://archive.org/download/tiny1125h2/Pro%20N.iso${RESET} <-"
echo -e "     - und baue damit eine  ${YELLOW}KVM${RESET}."
echo -e ""
echo -e "${CYAN}  ------------------------------------------------------------${RESET}"
read -p "$(echo -e "${BOLD}  Drücke [ENTER] um einen 3-Phasen-Testlauf zu starten...${RESET}")"

# Simulation mit Dummy-Werten
X_CALIB=500
Y_CALIB=1200
X_SHUTTER=960
Y_SHUTTER=2100
CALIB_ZEIT=3

for ((i=1; i<=3; i++))
do
    $CLEAR
    echo -e "${BOLD}${YELLOW}  🧪 TESTLAUF: SCHLEIFE $i VON 3${RESET}\n"
    echo -e "  🤖 Sende Klick an Kalibrierung (X: $X_CALIB, Y: $Y_CALIB)..."
    adb shell input tap $X_CALIB $Y_CALIB >/dev/null 2>&1

    echo -e "  ⏳ Warte CALIB_ZEIT ($CALIB_ZEIT Sek. Shutter offen)..."
    sleep $CALIB_ZEIT

    echo -e "  📸 Sende Klick an Foto-Auslöser (X: $X_SHUTTER, Y: $Y_SHUTTER)..."
    adb shell input tap $X_SHUTTER $Y_SHUTTER >/dev/null 2>&1

    if [ $i -lt 3 ]; then sleep 5; fi
done

echo -e "\n${GREEN}  ✅ Testlauf beendet! Trage die echten Werte nun ins Haupt-Skript ein.${RESET}"
exit 0
