import asyncio

from nicegui import ui

from modules.services import CoverCacheError, DiscogsError

from .common import SERVICE, page_frame


@ui.page('/scan')
def scan_panel() -> None:
    with page_frame('Scan and register'):
        barcode = ui.input('Barcode / EAN / UPC').props('outlined dense').classes('w-full')
        with ui.row().classes('ktom-scan-layout w-full flex-1 gap-5'):
            with ui.column().classes('ktom-frame flex-1 items-center justify-center gap-4 p-8'):
                camera_preview = ui.element('video').props(
                    'id=ktom-camera autoplay muted playsinline aria-label="Camera preview"'
                ).classes(
                    'h-64 w-full max-w-xl bg-black object-cover border border-gray-700'
                )
                camera_toggle = ui.button('Reactivate camera', icon='play_arrow').props(
                    'outline color=amber-6'
                ).classes('hidden')
                ui.label('CAMERA READY').classes('ktom-label')
                ui.label('EAN / UPC / BARCODE').classes('text-xl')
                camera_status = ui.label('Camera is inactive').classes('text-sm text-gray-400')

                async def assign_camera(device_id: str, dialog: ui.dialog) -> None:
                    await ui.run_javascript(
                        f"localStorage.setItem('ktom_camera_pc', '{device_id}'); return true;"
                    )
                    ui.notify('Kamera tilldelad.')
                    dialog.close()

                async def open_camera_setup() -> None:
                    devices = await ui.run_javascript('''
                        (async () => {
                            try {
                                const unlock = await navigator.mediaDevices.getUserMedia({video: true, audio: false});
                                unlock.getTracks().forEach(track => track.stop());
                            } catch (error) {
                                return [];
                            }
                            const devices = await navigator.mediaDevices.enumerateDevices();
                            return devices
                                .filter(device => device.kind === 'videoinput')
                                .map(device => ({deviceId: device.deviceId, label: device.label || 'Okänd kamera'}));
                        })()
                    ''', timeout=15.0) or []
                    if not devices:
                        ui.notify('Ingen kamera hittades.')
                        return
                    with ui.dialog() as dialog, ui.card().classes('ktom-frame gap-3 p-6'):
                        ui.label('Kamerainställning').classes('text-xl font-bold')
                        ui.label('Välj vilken PC-kamera som ska användas.').classes('text-sm text-gray-400')
                        for device in devices:
                            with ui.row().classes('w-full items-center justify-between gap-3'):
                                ui.label(device['label']).classes('text-sm')
                                ui.button(
                                    'Använd', on_click=lambda d=device: assign_camera(d['deviceId'], dialog)
                                ).props('outline dense')
                        ui.button('Stäng', on_click=dialog.close).props('flat')
                    dialog.open()

                ui.button('Kamerainställning', icon='tune', on_click=open_camera_setup).props('flat dense')

                async def activate_camera() -> None:
                    camera_preview.classes(remove='hidden')
                    camera_toggle.classes(add='hidden')
                    script = '''
                        (async () => {
                            const camera = document.getElementById('ktom-camera');
                            const storedId = localStorage.getItem('ktom_camera_pc');
                            const constraints = storedId
                                ? {video: {deviceId: {exact: storedId}}, audio: false}
                                : {video: {facingMode: {ideal: 'user'}}, audio: false};
                            let stream;
                            try {
                                stream = await navigator.mediaDevices.getUserMedia(constraints);
                            } catch (error) {
                                return {error: 'Camera permission or camera access failed.'};
                            }
                            camera.srcObject = stream;
                            await fetch('/camera/barcode?clear=true');
                            const canvas = document.createElement('canvas');
                            const context = canvas.getContext('2d');
                            await new Promise(resolve => setTimeout(resolve, 500));
                            const deadline = Date.now() + 30000;
                            while (Date.now() < deadline) {
                                if (!camera.videoWidth || !camera.videoHeight) {
                                    await new Promise(resolve => setTimeout(resolve, 250));
                                    continue;
                                }
                                canvas.width = camera.videoWidth;
                                canvas.height = camera.videoHeight;
                                context.drawImage(camera, 0, 0, canvas.width, canvas.height);
                                const image = await new Promise(resolve => canvas.toBlob(resolve, 'image/jpeg', 0.85));
                                const decoded = await fetch('/camera/decode', {
                                    method: 'POST',
                                    headers: {'Content-Type': 'image/jpeg'},
                                    body: image,
                                });
                                const data = await decoded.json();
                                if (data.barcode) {
                                    stream.getTracks().forEach(track => track.stop());
                                    camera.srcObject = null;
                                    return {code: data.barcode};
                                }
                                await new Promise(resolve => setTimeout(resolve, 250));
                            }
                            stream.getTracks().forEach(track => track.stop());
                            camera.srcObject = null;
                            return {error: 'No barcode detected within 30 seconds.'};
                        })()
                    '''
                    result = await ui.run_javascript(script, timeout=35.0)
                    result = result or {}
                    if result.get('code'):
                        barcode.value = result['code']
                        camera_preview.classes(add='hidden')
                        camera_toggle.classes(remove='hidden')
                        camera_status.set_text(f"Barcode detected: {result['code']}. Searching Discogs...")
                        ui.notify('Barcode detected; searching Discogs')
                        await lookup()
                    else:
                        camera_status.set_text(result.get('error', 'Automatic scan failed'))

                ui.button('Activate camera', icon='play_arrow', on_click=activate_camera).props(
                    'unelevated color=amber-8'
                )
                camera_toggle.on('click', activate_camera)

                async def stop_camera() -> None:
                    await ui.run_javascript('''
                        (() => {
                            const camera = document.getElementById('ktom-camera');
                            if (camera && camera.srcObject) {
                                camera.srcObject.getTracks().forEach(track => track.stop());
                                camera.srcObject = null;
                            }
                            return true;
                        })()
                    ''')
                    camera_status.set_text('Camera stopped')

                ui.button('Stop camera', icon='stop', on_click=stop_camera).props('outline color=grey-6')
            with ui.column().classes('ktom-frame flex-1 gap-3 p-6'):
                ui.label('Release preview').classes('text-xl font-bold')
                artist = ui.input('Artist').props('outlined dense').classes('w-full')
                title = ui.input('Album title').props('outlined dense').classes('w-full')
                catalog_number = ui.input('Catalog number').props('outlined dense').classes('w-full')
                release_year = ui.input('Release year').props('outlined dense').classes('w-full')
                media_type = ui.input('Media type').props('outlined dense').classes('w-full')
                duration = ui.input('Duration').props('outlined dense').classes('w-full')
                release_type = ui.input('Release type').props('outlined dense').classes('w-full')
                purchase_price = ui.input('Purchase price (SEK)').props('outlined dense').classes('w-full')
                discogs_min = ui.input('Discogs minimum (SEK)').props('outlined dense').classes('w-full')
                discogs_median = ui.input('Discogs median (SEK)').props('outlined dense').classes('w-full')
                discogs_max = ui.input('Discogs maximum (SEK)').props('outlined dense').classes('w-full')
                cover_preview = ui.image().classes('hidden h-40 w-40 object-cover')
                credits = ui.textarea('Credits').props('outlined autogrow').classes('w-full')
                status = ui.label('').classes('text-sm text-gray-400')
                lookup_payload: dict[str, object] = {}

                async def lookup() -> None:
                    nonlocal lookup_payload
                    try:
                        lookup_payload = await asyncio.to_thread(
                            SERVICE.discogs.lookup_barcode, barcode.value or ''
                        )
                        artist.value = lookup_payload.get('artist', '')
                        title.value = lookup_payload.get('title', '')
                        catalog_number.value = lookup_payload.get('catalog_number', '')
                        release_year.value = str(lookup_payload.get('release_year') or '')
                        media_type.value = lookup_payload.get('media_type', '')
                        duration.value = lookup_payload.get('duration', '')
                        release_type.value = lookup_payload.get('release_type', '')
                        purchase_price.value = str(lookup_payload.get('purchase_price') or '')
                        discogs_min.value = str(lookup_payload.get('discogs_min') or '')
                        discogs_median.value = str(lookup_payload.get('discogs_median') or '')
                        discogs_max.value = str(lookup_payload.get('discogs_max') or '')
                        credits.value = lookup_payload.get('credits', '')
                        cover_url = lookup_payload.get('cover_url')
                        if cover_url:
                            cover_preview.set_source(str(cover_url))
                            cover_preview.classes(remove='hidden')
                        status.set_text('Discogs data loaded. Review and save.')
                    except (DiscogsError, ValueError) as error:
                        status.set_text(str(error))

                async def save() -> None:
                    try:
                        saved = SERVICE.save({
                            **lookup_payload,
                            'barcode': barcode.value,
                            'artist': artist.value,
                            'title': title.value,
                            'catalog_number': catalog_number.value,
                            'release_year': release_year.value,
                            'media_type': media_type.value,
                            'duration': duration.value,
                            'release_type': release_type.value,
                            'purchase_price': purchase_price.value,
                            'discogs_min': discogs_min.value,
                            'discogs_median': discogs_median.value,
                            'discogs_max': discogs_max.value,
                            'credits': credits.value,
                        })
                        status.set_text('Record saved to SQLite.')
                        if saved.cover_url and saved.id:
                            try:
                                await asyncio.to_thread(SERVICE.cache_cover, saved.id)
                                status.set_text('Record saved and cover cached.')
                            except CoverCacheError as error:
                                status.set_text(f'Record saved; cover cache skipped: {error}')
                        ui.notify('Record saved')
                    except ValueError as error:
                        status.set_text(str(error))

                with ui.row().classes('gap-2'):
                    ui.button('Discogs lookup', icon='cloud_download', on_click=lookup).props(
                        'outline color=amber-6'
                    )
                    ui.button('Approve / save', icon='save', on_click=save).props(
                        'unelevated color=green-8'
                    )
