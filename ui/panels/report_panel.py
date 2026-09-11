from nicegui import ui

from .common import SERVICE, page_frame


@ui.page('/reports')
def report_panel() -> None:
    with page_frame('Report and print'):
        with ui.column().classes('ktom-frame max-w-3xl gap-5 p-6'):
            ui.label('Binder archive export').classes('text-2xl font-bold')
            ui.label('Two pages per record: cover reference followed by structured metadata.').classes('text-gray-400')
            status = ui.label('').classes('text-sm text-green-400')

            def export() -> None:
                try:
                    path = SERVICE.export_docx()
                    status.set_text(f'Exported {path.name} to {path.parent}')
                except Exception as error:
                    status.set_text(str(error))

            ui.button('Create report', icon='picture_as_pdf', on_click=export).props('unelevated color=amber-8')
