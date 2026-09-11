import tempfile
import unittest
from pathlib import Path

from modules.database import CURRENT_SCHEMA_VERSION, Database
from modules.services import RecordService


class DatabaseTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.service = RecordService(Database(Path(self.temp_dir.name) / 'test.sqlite3'))

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_schema_and_record_lifecycle(self) -> None:
        record = self.service.save({
            'barcode': '123',
            'artist': 'Massive Attack',
            'title': 'Blue Lines',
        })
        self.assertEqual(record.title, 'Blue Lines')
        self.assertEqual(self.service.search('massive')[0].id, record.id)

        updated = self.service.update(record.id, {'title': 'Blue Lines Remastered'})
        self.assertEqual(updated.title, 'Blue Lines Remastered')
        self.assertTrue(self.service.delete(record.id))
        self.assertIsNone(self.service.get(record.id))

        connection = self.service.database.connect()
        try:
            version = connection.execute('PRAGMA user_version').fetchone()[0]
        finally:
            connection.close()
        self.assertEqual(version, CURRENT_SCHEMA_VERSION)

    def test_report_export_is_recorded(self) -> None:
        self.service.save({'artist': 'Pink Floyd', 'title': 'The Wall'})
        output_path = self.service.export_csv()
        self.assertTrue(output_path.exists())
        self.assertEqual(len(self.service.database.reports()), 1)
        self.assertEqual(self.service.statistics()['reports'], 1)

    def test_database_backup_is_readable(self) -> None:
        self.service.save({'artist': 'Joy Division', 'title': 'Unknown Pleasures'})
        backup_path = Path(self.temp_dir.name) / 'backups' / 'copy.sqlite3'
        self.service.backup_database(backup_path)
        backup_service = RecordService(Database(backup_path))
        self.assertEqual(backup_service.statistics()['records'], 1)


if __name__ == '__main__':
    unittest.main()
