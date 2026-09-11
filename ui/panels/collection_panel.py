from nicegui import ui

from .common import SERVICE, navigate, page_frame


@ui.page('/collection')
def collection_panel(tray: int = 0) -> None:
    records = SERVICE.search(limit=1000)
    with page_frame('Record trays'):
        if not records:
            ui.label('No records in the archive yet.').classes('mx-auto mt-16 text-gray-500')
            return
        tray_count = (len(records) + 74) // 75
        page_index = {'value': max(0, min(tray // 2, (tray_count - 1) // 2))}
        tray_content = ui.column().classes('w-full gap-4')

        def render_page() -> None:
            tray_content.clear()
            first_tray = page_index['value'] * 2
            with tray_content:
                for tray_index in range(first_tray, min(first_tray + 2, tray_count)):
                    tray_records = records[tray_index * 75:(tray_index + 1) * 75]
                    with ui.column().classes('ktom-frame w-full gap-3 p-4'):
                        with ui.row().classes('w-full items-center justify-between'):
                            ui.label(f'TRAY {tray_index + 1:02d}').classes('ktom-label')
                            ui.label(f'{len(tray_records)} / 75 RECORDS').classes('ktom-label text-amber-400')
                        with ui.element('div').classes('ktom-tray'):
                            for record in tray_records:
                                spine = ui.element('div').classes('ktom-spine cursor-pointer p-2 text-xs')
                                spine.on(
                                    'click',
                                    lambda record_id=record.id, tray_number=tray_index: navigate(
                                        f'/record/{record_id}?tray={tray_number}'
                                    ),
                                )
                                with spine:
                                    ui.label(record.artist).classes('font-bold')
                                    ui.label(record.title).classes('text-gray-400')
            page_status.set_text(f'Trays {first_tray + 1}-{min(first_tray + 2, tray_count)} of {tray_count}')
            previous_button.set_enabled(page_index['value'] > 0)
            next_button.set_enabled(first_tray + 2 < tray_count)

        def move_page(step: int) -> None:
            page_index['value'] = max(0, min(page_index['value'] + step, (tray_count - 1) // 2))
            render_page()

        with ui.row().classes('w-full items-center justify-between'):
            previous_button = ui.button('Previous trays', icon='arrow_back', on_click=lambda: move_page(-1))
            page_status = ui.label('').classes('ktom-label text-amber-400')
            next_button = ui.button('Next trays', icon='arrow_forward', on_click=lambda: move_page(1))
        tray_surface = ui.element('div').props('id=ktom-tray-surface').classes('w-full')
        tray_surface.on('swipe', lambda event: move_page(1 if event.args.get('direction') == 'left' else -1))
        with tray_surface:
            render_page()
