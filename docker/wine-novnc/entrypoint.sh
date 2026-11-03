#!/usr/bin/env bash
set -euo pipefail

RESOLUTION="${RESOLUTION:-1280x800x24}"
DISPLAY_NUM="${DISPLAY#:}"
DISPLAY_NUM="${DISPLAY_NUM:-0}"
export DISPLAY=":${DISPLAY_NUM}"
export WINEPREFIX="${WINEPREFIX:-/wineprefix}"
export WINEARCH="${WINEARCH:-win64}"
export WINEDEBUG="${WINEDEBUG:--all}"
APP_DIR="${APP_DIR:-/opt/app}"
DATA_DIR="${DATA_DIR:-/data}"
NOVNC_HOME="${NOVNC_HOME:-/opt/novnc}"
APP_EXE_NAME="${APP_EXE_NAME:-RawStrengthEmployeeAuditManager.exe}"
PORT="${PORT:-8080}"
VNC_PASSWORD="${VNC_PASSWORD:-}"
APP_DOWNLOAD_URL="${APP_DOWNLOAD_URL:-}"

log() { echo "[entrypoint] $*"; }

mkdir -p "$APP_DIR" "$DATA_DIR" "$WINEPREFIX" /tmp/.X11-unix
chmod 1777 /tmp/.X11-unix || true

# ---------------------------------------------------------------------------
# 1) Virtual display
# ---------------------------------------------------------------------------
log "Starting Xvfb on $DISPLAY ($RESOLUTION)"
Xvfb "$DISPLAY" -screen 0 "$RESOLUTION" -ac +extension GLX +render -noreset &
XVFB_PID=$!
sleep 1

# ---------------------------------------------------------------------------
# 2) Window manager (borderless-friendly)
# ---------------------------------------------------------------------------
log "Starting Openbox"
openbox &
OPENBOX_PID=$!
sleep 1

# ---------------------------------------------------------------------------
# 3) VNC server (shared display for noVNC)
# ---------------------------------------------------------------------------
VNC_ARGS=(-display "$DISPLAY" -forever -shared -rfbport 5900 -localhost)
if [[ -n "$VNC_PASSWORD" ]]; then
  mkdir -p "$HOME/.vnc"
  x11vnc -storepasswd "$VNC_PASSWORD" "$HOME/.vnc/passwd"
  VNC_ARGS+=(-rfbauth "$HOME/.vnc/passwd")
else
  # Render demo / internal use — set VNC_PASSWORD in production
  VNC_ARGS+=(-nopw)
fi

log "Starting x11vnc"
x11vnc "${VNC_ARGS[@]}" &
X11VNC_PID=$!
sleep 1

# ---------------------------------------------------------------------------
# 4) noVNC / websockify on Render $PORT
# ---------------------------------------------------------------------------
NOVNC_WEB="${NOVNC_HOME}/www"
if [[ ! -d "$NOVNC_WEB" && -d /usr/share/novnc ]]; then
  NOVNC_WEB=/usr/share/novnc
fi
if [[ ! -d "$NOVNC_WEB" ]]; then
  log "ERROR: noVNC web assets not found"
  exit 1
fi

log "Starting websockify/noVNC on 0.0.0.0:${PORT}"
websockify --web "$NOVNC_WEB" "${PORT}" localhost:5900 &
WEBSOCKIFY_PID=$!
sleep 1

# ---------------------------------------------------------------------------
# 5) Obtain / locate untouched Windows application
# ---------------------------------------------------------------------------
find_exe() {
  find "$APP_DIR" -type f -iname "$APP_EXE_NAME" 2>/dev/null | head -n1
}

EXE_PATH="$(find_exe || true)"

if [[ -z "$EXE_PATH" && -n "$APP_DOWNLOAD_URL" ]]; then
  log "Downloading application package from APP_DOWNLOAD_URL"
  curl -fsSL -L -o /tmp/app_download.bin "$APP_DOWNLOAD_URL"
  if file /tmp/app_download.bin | grep -qi 'zip'; then
    unzip -o /tmp/app_download.bin -d "$APP_DIR"
  elif file /tmp/app_download.bin | grep -qi '7-zip\|7z'; then
    7z x -o"$APP_DIR" /tmp/app_download.bin
  else
    cp /tmp/app_download.bin "$APP_DIR/setup.exe"
    log "Running Windows installer under Wine (silent when possible)"
    wineboot -u || true
    winetricks -q vcrun2019 || winetricks -q vcrun2015 || true
    wine "$APP_DIR/setup.exe" /VERYSILENT /NORESTART /DIR='C:\AuditApp' || \
      wine "$APP_DIR/setup.exe" /S || \
      wine "$APP_DIR/setup.exe" || true
    for candidate in \
      "$WINEPREFIX/drive_c/AuditApp" \
      "$WINEPREFIX/drive_c/Program Files/Raw Strength Employee Audit Manager" \
      "$WINEPREFIX/drive_c/Program Files (x86)/Raw Strength Employee Audit Manager"
    do
      if [[ -d "$candidate" ]]; then
        cp -a "$candidate/." "$APP_DIR/" || true
      fi
    done
  fi
  EXE_PATH="$(find_exe || true)"
fi

if [[ -z "$EXE_PATH" ]]; then
  if [[ -f "$APP_DIR/$APP_EXE_NAME" ]]; then
    EXE_PATH="$APP_DIR/$APP_EXE_NAME"
  fi
fi

if [[ -z "$EXE_PATH" || ! -f "$EXE_PATH" ]]; then
  log "ERROR: $APP_EXE_NAME not found under $APP_DIR"
  log "Set APP_DOWNLOAD_URL to the GitHub release Setup.exe or place the onedir build in $APP_DIR"
  wait "$WEBSOCKIFY_PID"
  exit 1
fi

log "Found application: $EXE_PATH"

# Persist app data: %LOCALAPPDATA%\EmployeeAuditManager -> /data
mkdir -p "$DATA_DIR/EmployeeAuditManager"
LOCALAPPDATA_WIN="$WINEPREFIX/drive_c/users/appuser/AppData/Local"
mkdir -p "$LOCALAPPDATA_WIN"
if [[ ! -L "$LOCALAPPDATA_WIN/EmployeeAuditManager" ]]; then
  rm -rf "$LOCALAPPDATA_WIN/EmployeeAuditManager" 2>/dev/null || true
  ln -s "$DATA_DIR/EmployeeAuditManager" "$LOCALAPPDATA_WIN/EmployeeAuditManager"
fi

if [[ ! -f "$WINEPREFIX/.bootstrapped" ]]; then
  log "Bootstrapping Wine prefix"
  wineboot -u || true
  winetricks -q vcrun2019 || winetricks -q vcrun2015 || true
  touch "$WINEPREFIX/.bootstrapped"
fi

# ---------------------------------------------------------------------------
# 6) Launch untouched EXE via Wine
# ---------------------------------------------------------------------------
cleanup() {
  log "Shutting down..."
  kill "$APP_PID" 2>/dev/null || true
  kill "$WEBSOCKIFY_PID" 2>/dev/null || true
  kill "$X11VNC_PID" 2>/dev/null || true
  kill "$OPENBOX_PID" 2>/dev/null || true
  kill "$XVFB_PID" 2>/dev/null || true
}
trap cleanup SIGTERM SIGINT EXIT

log "Launching EXE with Wine (no modifications to the binary)"
cd "$(dirname "$EXE_PATH")"
wine "$(basename "$EXE_PATH")" &
APP_PID=$!

log "Ready — open http://<host>:${PORT}/vnc.html?autoconnect=1&resize=remote"
wait "$APP_PID" || true
wait "$WEBSOCKIFY_PID"
