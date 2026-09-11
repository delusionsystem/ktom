import unittest

from modules.config import Settings
from modules.services import DiscogsClient


class ServiceTests(unittest.TestCase):
    def test_discogs_release_payload(self) -> None:
        release = {
            'id': 42,
            'title': 'Test Album',
            'artists': [{'name': 'Test Artist'}],
            'labels': [{'catno': 'ABC-1'}],
            'formats': [{'name': 'Vinyl'}],
            'year': 1980,
            'tracklist': [{'duration': '3:45'}, {'duration': '4:20'}],
            'images': [{'uri': 'https://example.test/cover.jpg'}],
            'type': 'release',
            'extraartists': [{'name': 'Producer', 'role': 'producer'}],
        }
        payload = DiscogsClient._release_payload(release, '123')
        payload.update(DiscogsClient._price_payload({
            'lowest_price': {'value': 10},
            'median_price': {'value': 20},
            'highest_price': {'value': 30},
        }))
        self.assertEqual(payload['discogs_release_id'], 42)
        self.assertEqual(payload['duration'], '8:05')
        self.assertEqual(payload['price_currency'], 'SEK')

    def test_settings_reject_invalid_port(self) -> None:
        original = __import__('os').environ.get('KTOM_PORT')
        __import__('os').environ['KTOM_PORT'] = 'invalid'
        try:
            with self.assertRaises(ValueError):
                Settings.from_environment()
        finally:
            if original is None:
                __import__('os').environ.pop('KTOM_PORT', None)
            else:
                __import__('os').environ['KTOM_PORT'] = original


if __name__ == '__main__':
    unittest.main()
