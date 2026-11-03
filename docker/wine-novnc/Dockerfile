# Stream the untouched Windows Employee Audit Manager EXE to a browser via Wine + noVNC.
# The .exe is not modified, decompiled, or re-coded.

FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive \
    WINEPREFIX=/wineprefix \
    WINEARCH=win64 \
    DISPLAY=:0 \
    RESOLUTION=1280x800x24 \
    HOME=/home/appuser \
    APP_DIR=/opt/app \
    DATA_DIR=/data \
    NOVNC_HOME=/opt/novnc

# 32-bit multiarch is required by many Windows runtimes under Wine
RUN dpkg --add-architecture i386 \
    && apt-get update \
    && apt-get install -y --no-install-recommends \
        ca-certificates \
        curl \
        wget \
        gnupg \
        software-properties-common \
        xvfb \
        x11vnc \
        openbox \
        xterm \
        novnc \
        websockify \
        supervisor \
        cabextract \
        unzip \
        p7zip-full \
        winbind \
        fonts-liberation \
        fonts-dejavu-core \
        libgl1 \
        libasound2 \
    && apt-get install -y --no-install-recommends wine64 wine32 wine \
    && rm -rf /var/lib/apt/lists/*

# winetricks for VC++ runtime (common PyInstaller / MSVC dependency)
RUN curl -fsSL -o /usr/local/bin/winetricks \
        https://raw.githubusercontent.com/Winetricks/winetricks/master/src/winetricks \
    && chmod +x /usr/local/bin/winetricks

RUN useradd -m -u 1000 -s /bin/bash appuser \
    && mkdir -p "$WINEPREFIX" "$APP_DIR" "$DATA_DIR" "$NOVNC_HOME" \
        /home/appuser/.config/openbox \
        /var/log/supervisor \
    && chown -R appuser:appuser /wineprefix /opt /data /home/appuser /var/log/supervisor

# Prefer system noVNC; keep a fallback copy path stable for websockify
RUN if [ -d /usr/share/novnc ]; then \
      ln -sfn /usr/share/novnc "$NOVNC_HOME/www"; \
    else \
      echo "ERROR: novnc package did not install /usr/share/novnc" && exit 1; \
    fi

COPY docker/wine-novnc/openbox-rc.xml /home/appuser/.config/openbox/rc.xml
COPY docker/wine-novnc/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh \
    && chown -R appuser:appuser /home/appuser/.config

USER appuser
WORKDIR /home/appuser

# Optional: bake a release URL at build time (otherwise set APP_DOWNLOAD_URL at runtime)
ARG APP_DOWNLOAD_URL=""
ENV APP_DOWNLOAD_URL=${APP_DOWNLOAD_URL} \
    APP_EXE_NAME=RawStrengthEmployeeAuditManager.exe \
    VNC_PASSWORD="" \
    PORT=8080

EXPOSE 8080
VOLUME ["/data"]

ENTRYPOINT ["/entrypoint.sh"]
