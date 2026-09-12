const camera = document.querySelector('#camera');
const cameraWrap = document.querySelector('#camera-wrap');
const status = document.querySelector('#scan-status');
const askingPrice = document.querySelector('#asking-price');
const pricePanel = document.querySelector('#price-panel');
const checkPrice = document.querySelector('#check-price');
const result = document.querySelector('#price-result');
const priceSignal = document.querySelector('#price-signal');
const resultCover = document.querySelector('#result-cover');
const resultTitle = document.querySelector('#result-title');
const resultArtist = document.querySelector('#result-artist');
const resultCatalog = document.querySelector('#result-catalog');
const resultAskingPrice = document.querySelector('#result-asking-price');
const resultLowestPrice = document.querySelector('#result-lowest-price');
const resultAveragePrice = document.querySelector('#result-average-price');
const resultMedianPrice = document.querySelector('#result-median-price');
const resultHighestPrice = document.querySelector('#result-highest-price');
const savedLinks = document.querySelector('#saved-links');
let controls = null;
let pendingBarcode = null;
let pendingRelease = null;
let links = JSON.parse(localStorage.getItem('ktom-fair-links-v1') || '[]');

function loadZXing() {
    if (window.ZXingBrowser) return Promise.resolve(window.ZXingBrowser);
    return new Promise((resolve, reject) => {
        const sources = [
            'https://cdn.jsdelivr.net/npm/@zxing/browser@0.2.1/umd/zxing-browser.min.js',
            'https://unpkg.com/@zxing/browser@0.2.1/umd/zxing-browser.min.js',
        ];
        let index = 0;
        const tryNext = () => {
            if (window.ZXingBrowser) {
                resolve(window.ZXingBrowser);
                return;
            }
            if (index >= sources.length) {
                reject(new Error('BARCODE_SUPPORT'));
                return;
            }
            const script = document.createElement('script');
            script.src = sources[index++];
            script.onload = () => window.ZXingBrowser ? resolve(window.ZXingBrowser) : tryNext();
            script.onerror = tryNext;
            document.head.append(script);
        };
        tryNext();
    });
}

function loadLegacyZXing() {
    if (window.ZXing?.BrowserMultiFormatReader) return Promise.resolve(window.ZXing);
    return new Promise((resolve, reject) => {
        const sources = [
            'https://cdn.jsdelivr.net/npm/@zxing/library@0.21.3/umd/index.min.js',
            'https://unpkg.com/@zxing/library@0.21.3/umd/index.min.js',
        ];
        let index = 0;
        const tryNext = () => {
            if (window.ZXing?.BrowserMultiFormatReader) {
                resolve(window.ZXing);
                return;
            }
            if (index >= sources.length) {
                reject(new Error('BARCODE_SUPPORT'));
                return;
            }
            const script = document.createElement('script');
            script.src = sources[index++];
            script.onload = () => window.ZXing?.BrowserMultiFormatReader ? resolve(window.ZXing) : tryNext();
            script.onerror = tryNext;
            document.head.append(script);
        };
        tryNext();
    });
}

function formatPrice(value) {
    return Number.isFinite(value) ? `${Math.round(value)} kr` : 'Saknas';
}

function stopCamera() {
    if (!controls) return;
    controls.stopped = true;
    controls.readerControls?.stop();
    controls.reader?.reset();
    controls.stream?.getTracks().forEach(track => track.stop());
    camera.srcObject = null;
    controls = null;
}

function improveBarcodeView(stream) {
    const track = stream?.getVideoTracks?.()[0];
    if (!track?.getCapabilities || !track?.applyConstraints) return;
    const capabilities = track.getCapabilities();
    const zoom = capabilities.zoom;
    if (!zoom || zoom.max <= 1) return;
    const target = Math.min(2.5, zoom.max);
    track.applyConstraints({ advanced: [{ zoom: target }] }).catch(() => { });
}

async function addScan(barcode) {
    if (/^https?:\/\//i.test(barcode)) {
        links.unshift({ value: barcode, savedAt: new Date().toISOString() });
        localStorage.setItem('ktom-fair-links-v1', JSON.stringify(links));
        renderLinks();
        status.className = 'status status-success';
        status.textContent = 'Webbadress sparad lokalt. Nästa scanning startar.';
        return;
    }
    status.className = 'status status-neutral';
    status.textContent = `Barcode ${barcode} läst - hämtar skivinformation...`;
    try {
        pendingBarcode = barcode;
        pendingRelease = await lookupDiscogs(barcode);
        showReleaseInfo(pendingRelease, barcode);
        pricePanel.hidden = false;
        askingPrice.focus();
        status.textContent = 'Skivan hittad. Skriv säljarens pris.';
    } catch (error) {
        pendingBarcode = null;
        pendingRelease = null;
        pricePanel.hidden = true;
        status.className = 'status status-error';
        status.textContent = `Kunde inte hämta skivinformation: ${error.message}`;
    }
}

async function checkPendingPrice() {
    const asking = Number.parseFloat(askingPrice.value);
    if (!pendingBarcode || !Number.isFinite(asking) || asking < 0) {
        status.className = 'status status-error';
        status.textContent = 'Skriv ett giltigt begärt pris först.';
        askingPrice.focus();
        return;
    }
    showPriceResult(pendingRelease, pendingBarcode);
}

function showReleaseInfo(release, barcode) {
    result.hidden = false;
    priceSignal.className = 'price-signal price-unknown';
    priceSignal.textContent = 'ANGE BEGÄRT PRIS';
    resultCover.src = release.coverUrl || '';
    resultCover.hidden = !release.coverUrl;
    resultTitle.textContent = release.title || 'Okänd utgåva';
    resultArtist.textContent = release.artist || 'Okänd artist';
    resultCatalog.textContent = `Ryggnummer: ${release.catalogNumber || 'Saknas'} · Barcode: ${barcode}`;
    resultAskingPrice.textContent = 'Väntar på pris';
    resultLowestPrice.textContent = formatPrice(release.lowestPrice);
    resultAveragePrice.textContent = formatPrice(release.averagePrice);
    resultMedianPrice.textContent = formatPrice(release.medianPrice);
    resultHighestPrice.textContent = formatPrice(release.highestPrice);
}

function showPriceResult(release, barcode) {
    const asking = Number.parseFloat(askingPrice.value);
    const lowest = release.lowestPrice;
    const median = release.medianPrice;
    let signal = 'PRISDATA SAKNAS';
    let signalClass = 'price-unknown';
    let explanation = `Barcode: ${barcode}`;

    if (Number.isFinite(asking) && Number.isFinite(lowest)) {
        if (asking <= lowest) {
            signal = 'BRA PRIS';
            signalClass = 'price-good';
            explanation = 'Begärt pris ligger på eller under lägsta kända marknadspris.';
        } else if (!Number.isFinite(median) || asking <= median) {
            signal = 'OK';
            signalClass = 'price-fair';
            explanation = 'Begärt pris ligger inom den kända marknadsnivån.';
        } else {
            signal = 'DÅLIGT PRIS';
            signalClass = 'price-expensive';
            explanation = 'Begärt pris ligger över medianpriset på Discogs.';
        }
    }

    result.hidden = false;
    priceSignal.className = `price-signal ${signalClass}`;
    priceSignal.textContent = signal;
    resultCatalog.textContent = `Ryggnummer: ${release.catalogNumber || 'Saknas'} · ${explanation}`;
    resultAskingPrice.textContent = formatPrice(asking);
    resultLowestPrice.textContent = formatPrice(lowest);
    resultAveragePrice.textContent = formatPrice(release.averagePrice);
    resultMedianPrice.textContent = formatPrice(median);
    resultHighestPrice.textContent = formatPrice(release.highestPrice);
    status.className = 'status status-success';
    status.textContent = 'Prisbedömning klar.';
}

async function lookupDiscogs(barcode) {
    const query = new URLSearchParams({ barcode, type: 'release', per_page: '1' });
    const searchResponse = await fetch(`https://api.discogs.com/database/search?${query}`, { headers: { Accept: 'application/json' } });
    if (!searchResponse.ok) throw new Error(`Discogs HTTP ${searchResponse.status}`);
    const search = await searchResponse.json();
    const match = search.results?.[0];
    if (!match?.id) throw new Error('Ingen Discogs-träff');

    const releaseResponse = await fetch(`https://api.discogs.com/releases/${match.id}`, { headers: { Accept: 'application/json' } });
    if (!releaseResponse.ok) throw new Error(`Discogs HTTP ${releaseResponse.status}`);
    const release = await releaseResponse.json();
    const lowestPrice = release.lowest_price ?? release.marketplace_stats?.lowest_price?.value;
    const medianPrice = release.marketplace_stats?.median_price?.value ?? release.stats?.median_price?.value;
    const highestPrice = release.highest_price ?? release.marketplace_stats?.highest_price?.value;
    const numericPrices = [lowestPrice, medianPrice, highestPrice]
        .map(Number)
        .filter(Number.isFinite);
    const averagePrice = numericPrices.length
        ? numericPrices.reduce((total, price) => total + price, 0) / numericPrices.length
        : NaN;
    const catalogNumber = (release.labels || [])
        .map(label => label.catno)
        .filter(Boolean)
        .join(' / ');
    return {
        title: release.title || match.title,
        artist: (release.artists || []).map(artist => artist.name).join(', '),
        catalogNumber,
        coverUrl: release.images?.[0]?.uri || match.cover_image || '',
        lowestPrice: Number.isFinite(Number(lowestPrice)) ? Number(lowestPrice) * 11 : NaN,
        averagePrice: Number.isFinite(averagePrice) ? averagePrice * 11 : NaN,
        medianPrice: Number.isFinite(Number(medianPrice)) ? Number(medianPrice) * 11 : NaN,
        highestPrice: Number.isFinite(Number(highestPrice)) ? Number(highestPrice) * 11 : NaN,
    };
}

async function startCamera() {
    try {
        if (controls && !controls.stopped) return;
        if (!window.isSecureContext || !navigator.mediaDevices?.getUserMedia) throw new Error('HTTPS_REQUIRED');

        if (!('BarcodeDetector' in window)) {
            let zxing;
            try {
                zxing = await loadZXing();
            } catch {
                zxing = await loadLegacyZXing();
            }
            const Reader = zxing.BrowserMultiFormatReader;
            const reader = new Reader();
            controls = { stopped: false, reader };
            status.className = 'status status-neutral';
            status.textContent = 'Kamera aktiv - visa streckkoden för kameran.';
            if (reader.decodeFromConstraints) {
                controls.readerControls = await reader.decodeFromConstraints(
                    {
                        video: {
                            facingMode: { ideal: 'environment' },
                            width: { ideal: 1920 },
                            height: { ideal: 1080 },
                        },
                        audio: false,
                    },
                    camera,
                    async scanResult => {
                        if (!scanResult || !controls || controls.stopped) return;
                        stopCamera();
                        await addScan(scanResult.getText());
                    },
                );
            } else {
                controls.readerControls = await reader.decodeFromVideoDevice(
                    undefined,
                    camera,
                    async scanResult => {
                        if (!scanResult || !controls || controls.stopped) return;
                        stopCamera();
                        await addScan(scanResult.getText());
                    },
                );
            }
            improveBarcodeView(camera.srcObject);
            return;
        }

        let stream;
        try {
            stream = await navigator.mediaDevices.getUserMedia({
                video: {
                    facingMode: { ideal: 'environment' },
                    width: { ideal: 1920 },
                    height: { ideal: 1080 },
                },
                audio: false,
            });
        } catch (error) {
            if (error.name !== 'OverconstrainedError' && error.name !== 'NotFoundError') throw error;
            stream = await navigator.mediaDevices.getUserMedia({ video: true, audio: false });
        }
        improveBarcodeView(stream);
        camera.srcObject = stream;
        camera.muted = true;
        camera.setAttribute('playsinline', '');
        await camera.play();
        status.className = 'status status-neutral';
        status.textContent = 'Kamera aktiv - håll streckkoden nära och fyll rutan.';
        controls = { stream, stopped: false };

        if ('BarcodeDetector' in window) {
            const detector = new BarcodeDetector({ formats: ['ean_13', 'ean_8', 'upc_a', 'upc_e', 'code_128', 'qr_code'] });
            const scan = async () => {
                if (!controls || controls.stopped) return;
                try {
                    const results = await detector.detect(camera);
                    if (results.length && results[0].rawValue) {
                        stopCamera();
                        await addScan(results[0].rawValue);
                        return;
                    }
                } catch { }
                requestAnimationFrame(scan);
            };
            requestAnimationFrame(scan);
        }
    } catch (error) {
        stopCamera();
        status.className = 'status status-error';
        status.textContent = error.message === 'HTTPS_REQUIRED'
            ? 'Kameran kräver HTTPS. Öppna mässappen via en https-adress.'
            : error.message === 'BARCODE_SUPPORT'
                ? 'Barcode-stöd saknas. Kontrollera internetanslutningen och ladda om sidan.'
                : error.name === 'NotAllowedError'
                    ? 'Kameraåtkomst nekades. Tillåt kamera för Safari i iPadens inställningar.'
                    : error.name === 'NotReadableError'
                        ? 'Kameran används redan av en annan app eller flik.'
                        : `Kameran kunde inte startas (${error.name || 'okänt fel'}).`;
    }
}

cameraWrap.addEventListener('click', startCamera);
cameraWrap.addEventListener('keydown', event => {
    if (event.key === 'Enter' || event.key === ' ') {
        event.preventDefault();
        startCamera();
    }
});
checkPrice.addEventListener('click', checkPendingPrice);
document.querySelector('#scan-again').addEventListener('click', () => {
    result.hidden = true;
    pricePanel.hidden = true;
    askingPrice.value = '';
    pendingBarcode = null;
    pendingRelease = null;
    startCamera();
});

function renderLinks() {
    savedLinks.replaceChildren();
    if (!links.length) {
        savedLinks.textContent = 'Inga webbadresser sparade ännu.';
        return;
    }
    links.forEach(link => {
        const anchor = document.createElement('a');
        anchor.href = link.value;
        anchor.target = '_blank';
        anchor.rel = 'noopener noreferrer';
        anchor.textContent = link.value;
        savedLinks.append(anchor);
    });
}

renderLinks();