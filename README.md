# KTOM

KTOM is a local NiceGUI record archive with a dark landscape kiosk interface, SQLite persistence, browser barcode scanning, and optional Discogs enrichment.

## Setup

Use Python 3.12 or newer, create a virtual environment, and install the dependencies:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

Copy `.env.example` to `.env` or set the variables in the shell. `DISCOGS_TOKEN` is optional; without it, records can still be entered manually.

## Run

```powershell
python main.py
```

The app listens on all local network interfaces at port `8080` by default and opens Edge or Chrome with kiosk flags when available. From another device on the same Wi-Fi, open `http://<computer-lan-ip>:8080`. Set `KTOM_KIOSK_BROWSER=false` to keep the browser launch manual.

Windows Firewall must allow inbound TCP traffic on port `8080`. Camera access from an iPad generally requires HTTPS; manual barcode entry still works over local HTTP.

## Data

- SQLite database: `databases/ktom.sqlite3`
- Cached covers: `databases/covers/`
- CSV reports: `databases/reports/`

Existing databases migrate automatically through SQLite `PRAGMA user_version`.
Backups can be created from Python with `RecordService.backup_database()` and are written to `databases/backups/` by default.

## Device checklist

- Use `localhost` or HTTPS; browsers block camera access on ordinary HTTP hosts.
- Allow camera permission when prompted.
- Chrome and Edge use the native barcode detector when available.
- Other supported browsers use the ZXing browser fallback loaded from the CDN.
- Verify rear-camera selection, timeout behavior, and manual barcode entry on each target device.

For an offline kiosk deployment, vendor `@zxing/browser` into a local static asset and replace the CDN script in `ui/panels/common.py`.

## Report verification

DOCX reports are generated as two logical pages per record: a cover page followed by a facts page. Open a multi-record report in LibreOffice Writer or Word and verify duplex pagination with real cached cover images before production printing.

## Test

```powershell
python -m pytest
```

The tests use temporary databases and do not modify the local collection.
