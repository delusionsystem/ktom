import os
import logging
import shutil
import socket
import subprocess
import tempfile
import threading
from pathlib import Path

from nicegui import ui as nicegui_ui

from modules.config import Settings

import ui.panels.report_panel  # noqa: F401
import modules.camera  # noqa: F401
import ui.panels.collection_panel  # noqa: F401
import ui.panels.record_panel  # noqa: F401
import ui.panels.scan_panel  # noqa: F401
import ui.panels.search_panel  # noqa: F401
import ui.panels.start_panel  # noqa: F401
import ui.panels.statistics_panel  # noqa: F401


LOGGER = logging.getLogger(__name__)


def local_network_address() -> str:
	try:
		with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as connection:
			connection.connect(('8.8.8.8', 80))
			return connection.getsockname()[0]
	except OSError:
		return '127.0.0.1'


def launch_kiosk_browser(url: str) -> None:
	browser_candidates = (
		os.environ.get('PROGRAMFILES(X86)', ''),
		os.environ.get('PROGRAMFILES', ''),
		os.environ.get('LOCALAPPDATA', ''),
	)
	browser_paths = (
		Path(browser_candidates[0]) / 'Microsoft/Edge/Application/msedge.exe',
		Path(browser_candidates[1]) / 'Microsoft/Edge/Application/msedge.exe',
		Path(browser_candidates[2]) / 'Google/Chrome/Application/chrome.exe',
	)

	for browser_path in browser_paths:
		if browser_path.is_file():
			_launch_browser(str(browser_path), url)
			return

	browser = shutil.which('msedge') or shutil.which('chrome')
	if browser:
		_launch_browser(browser, url)
		return
	LOGGER.warning('No supported kiosk browser found; open %s manually', url)


def _launch_browser(browser: str, url: str) -> None:
	name = Path(browser).stem.lower()
	# Persistent (not per-PID) profile so the PC webcam permission for KTOM is remembered between launches.
	profile_dir = Path(tempfile.gettempdir()) / 'ktom-kiosk-profile'
	arguments = [
		browser,
		'--new-window',
		'--no-first-run',
		'--no-default-browser-check',
		f'--user-data-dir={profile_dir}',
		'--disable-session-crashed-bubble',
		'--kiosk',
		'--autoplay-policy=no-user-gesture-required',
		# Kiosk mode can hide the camera permission prompt entirely; auto-accept it instead.
		'--use-fake-ui-for-media-stream',
	]
	if name == 'msedge':
		arguments.append('--edge-kiosk-type=fullscreen')
	arguments.append(url)
	LOGGER.info('Launching kiosk browser: %s', arguments)
	try:
		subprocess.Popen(arguments)
	except OSError:
		LOGGER.exception('Could not launch kiosk browser %s', browser)


def console_menu(url: str) -> None:
	while True:
		print('\nKTOM')
		print('1. Öppna startsida')
		print('2. Avsluta KTOM')
		try:
			choice = input('Välj: ').strip()
		except (EOFError, KeyboardInterrupt):
			os._exit(0)
		if choice == '1':
			launch_kiosk_browser(url)
		elif choice == '2':
			os._exit(0)


if __name__ in {'__main__', '__mp_main__'}:
	logging.basicConfig(level=os.getenv('KTOM_LOG_LEVEL', 'INFO').upper())
	settings = Settings.from_environment()
	start_url = f'http://localhost:{settings.port}'
	if settings.kiosk_browser:
		threading.Timer(
			1.0,
			launch_kiosk_browser,
			args=(start_url,),
		).start()
		threading.Thread(target=console_menu, args=(start_url,), daemon=True).start()
	nicegui_ui.run(
		host=settings.host,
		port=settings.port,
		dark=True,
		viewport='width=device-width, initial-scale=1, maximum-scale=1, user-scalable=no',
		reload=False,
		show=False,
	)
