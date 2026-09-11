from nicegui import ui

from .common import SERVICE, cover_view, navigate, page_frame


@ui.page('/')
def start_panel() -> None:
    with page_frame('', compact=True):
        recent_records = SERVICE.recent()
        ui.label('STARTPANEL / SENAST INSCANNADE SKIVOR').classes('mb-4 ktom-label')
        with ui.row().classes('ktom-start-grid w-full'):
            for index in range(4):
                record = recent_records[index] if index < len(recent_records) else None
                cover_class = ('ktom-cover--blue', 'ktom-cover--red', 'ktom-cover--gold', '')[(index - 1) % 4]
                tile = ui.column().classes('ktom-history-tile flex-1 items-center justify-between p-4')
                if record:
                    tile.classes('cursor-pointer')
                    tile.on('click', lambda record_id=record.id: navigate(f'/record/{record_id}'))
                with tile:
                    if not record:
                        with ui.element('div').classes('ktom-cover ktom-cover--empty w-3/5 h-40'):
                            ui.icon('album', size='36px').classes('text-gray-600')
                        ui.label('INGEN POST').classes('ktom-label')
                    elif record.cover_url:
                        cover_view(record, 'w-3/5 h-40')
                    else:
                        with ui.element('div').classes('ktom-cover ' + cover_class + ' w-3/5 h-40'):
                            ui.label(record.title).classes('mt-4 block px-3 text-center text-lg font-bold text-white')
                    if record:
                        with ui.column().classes('w-full gap-0'):
                            ui.label(record.title).classes('text-lg font-bold')
                            ui.label(record.artist).classes('text-sm text-gray-400')
            with ui.column().classes('ktom-tile ktom-scan flex-1 cursor-pointer items-center justify-center gap-4 p-4') as scan_tile:
                scan_tile.on('click', lambda: navigate('/scan'))
                ui.icon('qr_code_scanner', size='64px').classes('text-white')
                ui.label('SCAN').classes('text-3xl font-bold tracking-[.2em] text-white')
                ui.label('Open camera').classes('ktom-label')
                ui.button('Open', icon='arrow_forward', on_click=lambda: navigate('/scan')).props('outline color=blue-6')
        with ui.row().classes('mt-5 w-full items-center justify-between border-t border-gray-700 pt-4'):
            ui.label(f'LOCAL SQLITE ARCHIVE / {len(SERVICE.search())} RECORDS CONNECTED').classes('ktom-label')
            ui.label('LANDSCAPE KIOSK').classes('ktom-label text-amber-400')
