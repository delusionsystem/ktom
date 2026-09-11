from nicegui import ui

from .common import SERVICE, page_frame


@ui.page('/stats')
def statistics_panel() -> None:
    with page_frame('Collection statistics'):
        stats = SERVICE.statistics()
        detail = SERVICE.statistics_detail()
        with ui.row().classes('w-full gap-4'):
            for value, label in ((stats['records'], 'Records'), (stats['artists'], 'Artists'), (stats['reports'], 'Reports')):
                with ui.column().classes('ktom-frame flex-1 gap-2 p-6'):
                    ui.label(value).classes('text-4xl font-bold text-amber-400')
                    ui.label(label).classes('ktom-label')
        with ui.row().classes('mt-6 w-full gap-5'):
            for title, key in (
                ('Top artists', 'artists'),
                ('Media types', 'media_types'),
                ('Release years', 'years'),
            ):
                with ui.column().classes('ktom-frame flex-1 gap-3 p-5'):
                    ui.label(title).classes('text-xl font-bold')
                    entries = detail[key]
                    if not entries:
                        ui.label('No data yet').classes('text-sm text-gray-500')
                    for entry in entries:
                        with ui.row().classes('w-full items-center justify-between'):
                            ui.label(str(entry['label'])).classes('text-sm')
                            ui.label(str(entry['count'])).classes('ktom-label text-amber-400')
