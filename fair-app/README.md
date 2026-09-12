# KTOM Massan

Fristående PWA-prototyp för Android, iPhone och iPad.

## Start lokalt

Node/npm behövs inte för prototypen. Från projektroten:

```powershell
python -m http.server 4173 --directory fair-app
```

Öppna sedan `http://localhost:4173` på PC:n. För kamera på en mobil krävs normalt HTTPS eller localhost på samma enhet.

## Fristående publicering

Mäss-appen kan publiceras separat på GitHub Pages utan KTOM-dator på mässan.
Workflow-filen `.github/workflows/deploy-fair-app.yml` publicerar endast denna
mapp. Efter att GitHub Pages har aktiverats med GitHub Actions blir adressen:

`https://delusionsystem.github.io/ktom/fair-app/`

## Prototypflöde

- Starta kameran.
- Läs barcode eller QR-URL i samma scannerpanel.
- Alla scanningar sparas i `localStorage` under den aktiva sessionen.
- QR-URL:er visas som klickbara länkar.
- Appen jämför säljarens begärda pris med Discogs marknadspris och visar
	`BRA PRIS`, `OK` eller `DÅLIGT PRIS` med färgkod.
- Inga scanningar sparas till KTOM-servern eller skickas till någon kö.
Prisbedömningen görs direkt efter scanning och begärt pris anges efter att
barcode har lästs.
Discogs-uppslagningen sker direkt i appen. Den här mappen är separat från desktopappen.
