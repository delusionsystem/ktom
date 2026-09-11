import unittest

from nicegui import app

import main  # noqa: F401


class UiRouteTests(unittest.TestCase):
    def test_application_routes_are_registered(self) -> None:
        expected = {
            '/', '/collection', '/record/{record_id}', '/scan',
            '/search', '/reports', '/stats',
        }
        actual = {route.path for route in app.routes if hasattr(route, 'path')}
        self.assertTrue(expected <= actual)


if __name__ == '__main__':
    unittest.main()
