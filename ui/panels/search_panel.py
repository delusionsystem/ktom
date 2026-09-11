from nicegui import ui

from .common import SERVICE, navigate, page_frame


@ui.page('/search')
def search_panel() -> None:
    with page_frame('Search archive'):
        query = ui.input('Artist, title, catalog number').props('outlined').classes('w-full')
        results = ui.column().classes('w-full gap-2')

        def search() -> None:
            results.clear()
            matches = SERVICE.search(query.value or '')
            with results:
                if not matches:
                    ui.label('No records found').classes('mx-auto mt-12 text-gray-500')
                for record in matches:
                    with ui.row().classes('ktom-frame w-full items-center justify-between p-4'):
                        with ui.column().classes('cursor-pointer gap-1').on(
                            'click', lambda record_id=record.id: navigate(f'/record/{record_id}')
                        ):
                            ui.label(f'{record.artist} - {record.title}').classes('text-lg')
                            ui.label(record.catalog_number or 'No catalog number').classes('ktom-label')
                        ui.button('Open', icon='arrow_forward', on_click=lambda record_id=record.id: navigate(
                            f'/record/{record_id}'
                        )).props('flat color=amber-6')

        ui.button('Search', icon='search', on_click=search).props('unelevated color=amber-8')
        search()
