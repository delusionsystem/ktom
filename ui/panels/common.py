import os
import threading

from nicegui import ui

from modules.database import Record
from modules.services import RecordService


SERVICE = RecordService()


STYLE = '''
<style>
    :root {
        --ktom-silver: #e3e7e8;
        --ktom-muted: #ffffff;
        --ktom-line: #343a3d;
        --ktom-accent: #5da9dc;
        --ktom-blue: #087ac1;
    }

    body {
        background:
            repeating-linear-gradient(120deg, rgba(255,255,255,.018) 0 1px, transparent 1px 6px),
            linear-gradient(135deg, #050607 0%, #0b0d0e 48%, #030405 100%);
        color: var(--ktom-silver);
        font-family: 'Trebuchet MS', 'Segoe UI', sans-serif;
        overflow: hidden;
    }

    .ktom-app {
        height: min(100vh, 768px);
        max-height: 768px;
        min-width: 900px;
        background:
            repeating-linear-gradient(60deg, rgba(255,255,255,.012) 0 1px, transparent 1px 7px),
            linear-gradient(60deg, #111314 0%, #080909 55%, #030404 100%);
        overflow: hidden;
    }

    .ktom-frame {
        border: 1px solid var(--ktom-line);
        border-radius: 8px;
        background: #131314;
        box-shadow: inset 0 1px rgba(255,255,255,.06), 0 12px 30px rgba(0,0,0,.28);
    }

    .ktom-tile {
        min-height: 260px;
        border: 1px solid #4b5558;
        border-radius: 8px;
        background: #131314;
        touch-action: manipulation;
        transition: transform .18s ease, border-color .18s ease, background .18s ease, filter .18s ease;
    }

    .ktom-tile:hover {
        border-color: var(--ktom-accent);
        background: linear-gradient(60deg, #25282a 0%, #131314 72%);
        filter: brightness(1.12);
        transform: translateY(-2px);
    }

    .ktom-tile:focus-within {
        border-color: var(--ktom-accent);
        background: linear-gradient(60deg, #25282a 0%, #131314 72%);
    }

    .ktom-history-tile {
        min-height: 260px;
        border: 1px solid #4b5558;
        border-radius: 8px;
        background: #131314;
    }

    .ktom-start-grid {
        display: grid !important;
        grid-template-columns: repeat(5, minmax(0, 1fr));
        gap: 12px;
    }

    .ktom-start-grid > * {
        min-width: 0;
        width: auto !important;
    }

    .ktom-cover--empty {
        display: flex;
        align-items: center;
        justify-content: center;
        background: linear-gradient(60deg, #252b2d, #101314 70%);
        border-style: dashed;
    }

    .ktom-cover {
        aspect-ratio: 1 / 1;
        background: linear-gradient(145deg, #744d32, #17100c 65%);
        border: 5px solid #0d1011;
        box-shadow: 0 8px 20px rgba(0,0,0,.45), inset 0 0 0 1px rgba(255,255,255,.2);
    }

    .ktom-cover--blue { background: linear-gradient(145deg, #31566c, #0c1419 68%); }
    .ktom-cover--red { background: linear-gradient(145deg, #863c38, #1b0c0d 68%); }
    .ktom-cover--gold { background: linear-gradient(145deg, #aa8b43, #201b0e 68%); }

    .ktom-scan {
        border: 1px solid var(--ktom-blue);
        border-radius: 8px;
        background: #131314;
    }

    .ktom-scan:hover,
    .ktom-scan:focus-within {
        background: linear-gradient(60deg, #15496a 0%, #131314 72%);
    }

    .ktom-tray {
        display: grid;
        grid-template-columns: repeat(15, minmax(34px, 1fr));
        gap: 5px;
    }

    .ktom-spine {
        min-height: 150px;
        border-left: 3px solid #9b8a68;
        border-right: 1px solid #697173;
        background: linear-gradient(90deg, #232a2c, #111516 70%);
        writing-mode: vertical-rl;
        transform: rotate(180deg);
        overflow: hidden;
        white-space: nowrap;
    }

    .ktom-label {
        color: var(--ktom-muted);
        font-size: 11px;
        letter-spacing: 1.2px;
        text-transform: uppercase;
    }

    .ktom-app .text-blue-400,
    .ktom-app .text-amber-400,
    .ktom-app .text-amber-500,
    .ktom-app .text-green-400,
    .ktom-app .text-gray-400,
    .ktom-app .text-gray-500,
    .ktom-app .text-gray-600 {
        color: #ffffff !important;
    }

    .ktom-language-button {
        color: var(--ktom-silver) !important;
        border: 1px solid var(--ktom-line);
        background: #131314 !important;
        min-height: 44px;
    }

    .ktom-language-button:hover,
    .ktom-language-button:focus-visible {
        color: #ffffff !important;
        border-color: #697276;
        background: #202325 !important;
    }

    .ktom-nav .q-btn {
        color: var(--ktom-silver) !important;
        background: #131314 !important;
        border: 1px solid #343a3d;
        box-shadow: inset 0 1px rgba(255,255,255,.04);
    }
    .ktom-nav .q-btn:hover,
    .ktom-nav .q-btn:focus-visible {
        color: #ffffff !important;
        background: #202325 !important;
        border-color: #697276;
    }
    .ktom-nav { flex-wrap: nowrap; }
    .ktom-nav .q-btn { min-width: 0; padding-left: 12px; padding-right: 12px; }
    .q-btn {
        border-radius: 6px;
        background-image: linear-gradient(45deg, rgba(255,255,255,.08), transparent 58%) !important;
        font-family: 'Trebuchet MS', 'Segoe UI', sans-serif;
        font-weight: 600;
        letter-spacing: .02em;
        min-height: 44px;
        padding-left: 16px;
        padding-right: 16px;
        touch-action: manipulation;
    }
    .q-btn--flat {
        background: transparent !important;
        background-image: none !important;
        box-shadow: none !important;
    }
    .q-btn:not(.q-btn--flat) {
        filter: brightness(.78) saturate(.9);
    }
    .q-focus-helper { display: none; }
    .ktom-scan-layout { display: flex; flex-direction: row; }
    .ktom-header-nav { flex: 1 1 auto; justify-content: center; }

    @media (hover: none) {
        .ktom-tile:active,
        .ktom-nav .q-btn:active,
        .q-btn:active {
            border-color: var(--ktom-blue);
            filter: brightness(1.15);
            transform: translateY(1px);
        }
    }

    @media (max-width: 900px) {
        body { overflow: auto; }
        .ktom-tile { min-height: 190px; }
        .ktom-history-tile { min-height: 190px; }
    }
</style>
'''


def navigate(path: str) -> None:
    ui.navigate.to(path)


def exit_ktom() -> None:
    threading.Timer(0.2, os._exit, args=(0,)).start()


def header() -> None:
    with ui.row().classes('w-full items-center justify-between px-6 py-4 ktom-frame'):
        with ui.row().classes('items-center gap-4'):
            ui.icon('album', size='30px').classes('text-amber-500')
            with ui.column().classes('gap-0'):
                ui.label('KTOM').classes('text-2xl font-bold tracking-[.35em]')
                ui.label('record archive / local station').classes('ktom-label')
        with ui.row().classes('ktom-header-nav items-center gap-1'):
            navigation('items-center gap-1')
        with ui.row().classes('items-center gap-3'):
            ui.button('SV', icon='language').props('flat').classes('ktom-language-button')
            ui.label('SYSTEM ONLINE').classes('ktom-label text-green-400')
            ui.icon('wifi', size='18px').classes('text-green-400')
            with ui.dialog() as exit_dialog, ui.card().classes('ktom-frame w-[min(90vw,420px)] gap-4 p-6'):
                ui.label('Avsluta KTOM?').classes('text-xl font-bold')
                ui.label('Servern stängs och kioskfönstret blir otillgängligt.').classes('text-sm text-gray-400')
                with ui.row().classes('w-full justify-end gap-2'):
                    ui.button('Avbryt', on_click=exit_dialog.close).props('flat')
                    ui.button('Avsluta', on_click=exit_ktom).props('unelevated color=red-7')
            with ui.menu() as menu:
                ui.menu_item('Öppna startsida', lambda: navigate('/'))
                ui.separator()
                ui.menu_item('Avsluta KTOM', exit_dialog.open)
            ui.button(icon='more_vert', on_click=menu.open).props('flat round dense').classes('text-gray-400')


def navigation(classes: str = 'w-full justify-center gap-1 px-4 py-2') -> None:
    items = (
        ('home', 'Start', '/'),
        ('view_carousel', 'Collection', '/collection'),
        ('qr_code_scanner', 'Scan', '/scan'),
        ('manage_search', 'Search', '/search'),
        ('description', 'Reports', '/reports'),
        ('insights', 'Stats', '/stats'),
    )
    with ui.row().classes(f'ktom-nav {classes}'):
        for icon, label, path in items:
            ui.button(label, icon=icon, on_click=lambda path=path: navigate(path)).props('flat').classes(
                'text-xs uppercase tracking-widest'
            )


def page_frame(title: str, compact: bool = False):
    ui.add_head_html(STYLE, shared=True)
    ui.add_head_html(
        '<meta name="google" content="notranslate">'
        '<meta http-equiv="Content-Language" content="sv">',
        shared=True,
    )
    with ui.column().classes('ktom-app w-full min-h-screen gap-0'):
        header()
        if title:
            title_classes = 'px-6 pt-3 text-2xl font-bold' if compact else 'px-6 pt-5 text-3xl font-bold'
            ui.label(title).classes(title_classes)
        return ui.column().classes('w-full flex-1 px-6 py-5')


def cover_view(record: Record, classes: str = 'w-full') -> None:
    if record.cover_url:
        ui.image(record.cover_url).classes(classes + ' object-cover')
        return
    with ui.element('div').classes('ktom-cover ' + classes):
        ui.label(record.title).classes('mt-4 block px-3 text-center text-lg font-bold text-white')
