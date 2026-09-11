from nicegui import ui

from .common import SERVICE, cover_view, navigate, page_frame


@ui.page('/record/{record_id}')
def record_panel(record_id: int, tray: int = 0) -> None:
    record = SERVICE.get(record_id)
    with page_frame('Record details'):
        if not record:
            ui.label('Record not found').classes('mx-auto mt-16 text-gray-500')
            ui.button('Back to collection', icon='arrow_back', on_click=lambda: navigate('/collection'))
            return
        with ui.row().classes('w-full flex-1 gap-6'):
            with ui.column().classes('ktom-frame w-2/5 items-center gap-4 p-6'):
                cover_view(record, 'w-full max-w-md')
                ui.button('Back to collection', icon='arrow_back', on_click=lambda: navigate(f'/collection?tray={tray}')).props(
                    'outline color=amber-6'
                )
            with ui.column().classes('ktom-frame flex-1 gap-3 p-6'):
                artist = ui.input('Artist', value=record.artist).props('outlined dense')
                title = ui.input('Album title', value=record.title).props('outlined dense')
                catalog_number = ui.input('Catalog number', value=record.catalog_number or '').props('outlined dense')
                media_type = ui.input('Media type', value=record.media_type or '').props('outlined dense')
                release_year = ui.input('Release year', value=str(record.release_year or '')).props('outlined dense')
                status = ui.label('').classes('text-sm text-gray-400')
                artist_records = SERVICE.by_artist(record.artist)
                if len(artist_records) > 1:
                    with ui.dialog() as artist_dialog, ui.card().classes('ktom-frame w-[min(90vw,700px)]'):
                        ui.label(f'{record.artist} covers').classes('text-xl font-bold')
                        with ui.carousel(animated=True, arrows=True, navigation=True).classes('w-full h-96'):
                            for artist_record in artist_records:
                                with ui.carousel_slide(name=str(artist_record.id)):
                                    cover_view(artist_record, 'h-80 w-full')
                                    ui.label(artist_record.title).classes('text-center')
                    ui.button('Artist covers', icon='collections', on_click=artist_dialog.open).props(
                        'outline color=amber-6'
                    )
                fields = (
                    ('Duration', record.duration),
                    ('Barcode', record.barcode),
                    ('Release type', record.release_type),
                    ('Discogs minimum', record.discogs_min),
                    ('Discogs median', record.discogs_median),
                    ('Discogs maximum', record.discogs_max),
                    ('Scanned', record.scanned_at),
                )
                for label, value in fields:
                    with ui.row().classes('w-full items-center justify-between border-b border-gray-800 py-2'):
                        ui.label(label).classes('ktom-label')
                        ui.label(str(value) if value is not None else 'Not specified')
                if record.credits:
                    ui.label('Credits').classes('ktom-label mt-3')
                    ui.label(record.credits).classes('max-h-32 overflow-auto text-xs text-gray-400')

                def save_changes() -> None:
                    try:
                        SERVICE.update(record.id, {
                            'artist': artist.value,
                            'title': title.value,
                            'catalog_number': catalog_number.value,
                            'media_type': media_type.value,
                            'release_year': release_year.value,
                        })
                        status.set_text('Changes saved.')
                    except (KeyError, ValueError) as error:
                        status.set_text(str(error))

                def delete_record() -> None:
                    SERVICE.delete(record.id)
                    navigate('/collection')

                with ui.row().classes('mt-4 gap-2'):
                    ui.button('Save changes', icon='save', on_click=save_changes).props('unelevated color=green-8')
                    ui.button('Delete record', icon='delete', on_click=delete_record).props('outline color=red-6')
