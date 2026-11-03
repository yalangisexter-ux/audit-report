# Stream untouched Windows EXE on Render (Wine + Xvfb + noVNC)

This stack runs the **exact** `RawStrengthEmployeeAuditManager` Windows build under Wine and streams the native GUI to a browser. The `.exe` is not decompiled, patched, or reimplemented.

## Architecture

Xvfb (:0) → Openbox → Wine(EXE) → x11vnc → websockify/noVNC → browser on `$PORT`

## Files

| Path | Role |
|------|------|
| `docker/wine-novnc/Dockerfile` | Ubuntu image with Wine, Xvfb, Openbox, x11vnc, noVNC |
| `docker/wine-novnc/entrypoint.sh` | Startup order + EXE launch |
| `docker/wine-novnc/openbox-rc.xml` | Borderless maximized windows |

## Prerequisites

1. Published Windows installer from GitHub Releases, e.g.  
   `https://github.com/yalangisexter-ux/audit-report/releases/download/v1.3.69/RawStrengthEmployeeAuditManager-Setup.exe`
2. Render account with **Docker** runtime.
3. Recommended: **Persistent Disk** mounted at `/data` (app DB / settings).

## Render settings

| Setting | Value |
|---------|--------|
| Runtime | Docker |
| Dockerfile path | `docker/wine-novnc/Dockerfile` |
| Docker context | repository root (`.`) |
| Instance | At least **1 GB RAM** (2 GB+ recommended for Wine + Qt) |
| Disk | Mount path `/data`, 1–5 GB |
| Health check | HTTP `/` or `/vnc.html` on `$PORT` |

### Environment variables

| Variable | Required | Description |
|----------|----------|-------------|
| `APP_DOWNLOAD_URL` | Yes (unless EXE baked in image) | Direct URL to Setup.exe or zip of onedir build |
| `APP_EXE_NAME` | No | Default `RawStrengthEmployeeAuditManager.exe` |
| `RESOLUTION` | No | Default `1280x800x24` |
| `VNC_PASSWORD` | Recommended | Password for the VNC session |
| `WINEDEBUG` | No | Default `-all` (quiet) |
| `PORT` | Set by Render | noVNC listen port |

Example:

```text
APP_DOWNLOAD_URL=https://github.com/yalangisexter-ux/audit-report/releases/download/v1.3.69/RawStrengthEmployeeAuditManager-Setup.exe
RESOLUTION=1280x800x24
VNC_PASSWORD=choose-a-strong-password
```

## Deploy steps (Render Dashboard)

1. **New → Web Service** → connect `yalangisexter-ux/audit-report`.
2. Runtime: **Docker**.
3. Dockerfile path: `docker/wine-novnc/Dockerfile`.
4. Set env vars above.
5. Add persistent disk → mount `/data`.
6. Deploy.
7. Open: `https://<your-service>.onrender.com/vnc.html?autoconnect=1&resize=remote`  
   (enter `VNC_PASSWORD` if set).

## Local smoke test

```bash
# From repo root
docker build -f docker/wine-novnc/Dockerfile -t audit-exe-stream .

docker run --rm -p 8080:8080 \
  -e PORT=8080 \
  -e APP_DOWNLOAD_URL="https://github.com/yalangisexter-ux/audit-report/releases/download/v1.3.69/RawStrengthEmployeeAuditManager-Setup.exe" \
  -e RESOLUTION=1280x800x24 \
  -v audit-data:/data \
  audit-exe-stream
```

Open http://localhost:8080/vnc.html?autoconnect=1

## Notes / limits

- First boot is slow (Wine prefix + VC++ redistributable + installer).
- Qt/PySide6 under Wine is best-effort; some GPU effects may differ from native Windows.
- This does **not** change the EXE, installer, or Windows release pipeline.
- Prefer a **standard** Render instance; free tier may OOM during Wine bootstrap.
- For production, always set `VNC_PASSWORD` and restrict who can open the service URL.
