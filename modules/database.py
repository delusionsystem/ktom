from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from threading import RLock
from typing import Any


DEFAULT_DATABASE_PATH = Path(__file__).resolve().parents[1] / 'databases' / 'ktom.sqlite3'
CURRENT_SCHEMA_VERSION = 3


class ManagedConnection(sqlite3.Connection):
    def __exit__(self, exception_type, exception, traceback):
        try:
            return super().__exit__(exception_type, exception, traceback)
        finally:
            self.close()


SCHEMA = '''
CREATE TABLE IF NOT EXISTS records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    barcode TEXT UNIQUE,
    discogs_release_id INTEGER,
    artist TEXT NOT NULL,
    title TEXT NOT NULL,
    catalog_number TEXT,
    media_type TEXT,
    release_year INTEGER,
    duration TEXT,
    purchase_price REAL,
    discogs_min REAL,
    discogs_median REAL,
    discogs_max REAL,
    price_currency TEXT,
    cover_url TEXT,
    release_type TEXT,
    credits TEXT,
    scanned_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_records_artist ON records(artist COLLATE NOCASE);
CREATE INDEX IF NOT EXISTS idx_records_title ON records(title COLLATE NOCASE);
CREATE INDEX IF NOT EXISTS idx_records_scanned_at ON records(scanned_at DESC);

CREATE TABLE IF NOT EXISTS reports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    file_path TEXT NOT NULL,
    format TEXT NOT NULL,
    query TEXT,
    record_count INTEGER NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
'''


@dataclass(frozen=True)
class Record:
    id: int | None
    barcode: str | None
    discogs_release_id: int | None
    artist: str
    title: str
    catalog_number: str | None = None
    media_type: str | None = None
    release_year: int | None = None
    duration: str | None = None
    purchase_price: float | None = None
    discogs_min: float | None = None
    discogs_median: float | None = None
    discogs_max: float | None = None
    price_currency: str | None = None
    cover_url: str | None = None
    cover_cached_path: str | None = None
    cover_cached_at: str | None = None
    release_type: str | None = None
    credits: str | None = None
    scanned_at: str | None = None
    updated_at: str | None = None

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> 'Record':
        return cls(**dict(row))


@dataclass(frozen=True)
class Report:
    id: int
    file_path: str
    format: str
    query: str | None
    record_count: int
    created_at: str


class Database:
    def __init__(self, path: str | Path = DEFAULT_DATABASE_PATH) -> None:
        self.path = Path(path)
        self._lock = RLock()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.initialize()

    def connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path, check_same_thread=False, factory=ManagedConnection)
        connection.row_factory = sqlite3.Row
        connection.execute('PRAGMA foreign_keys = ON')
        return connection

    def initialize(self) -> None:
        with self._lock, self.connect() as connection:
            connection.executescript(SCHEMA)
            version = connection.execute('PRAGMA user_version').fetchone()[0]
            if version < 2:
                self._add_column_if_missing(connection, 'discogs_release_id', 'INTEGER')
                self._add_column_if_missing(connection, 'price_currency', 'TEXT')
                version = 2
            if version < 3:
                self._add_column_if_missing(connection, 'cover_cached_path', 'TEXT')
                self._add_column_if_missing(connection, 'cover_cached_at', 'TEXT')
                connection.execute('''
                    CREATE TABLE IF NOT EXISTS reports (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        file_path TEXT NOT NULL,
                        format TEXT NOT NULL,
                        query TEXT,
                        record_count INTEGER NOT NULL,
                        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                version = 3
            connection.execute(f'PRAGMA user_version = {version}')

    @staticmethod
    def _add_column_if_missing(connection: sqlite3.Connection, column: str, definition: str) -> None:
        columns = {row['name'] for row in connection.execute('PRAGMA table_info(records)')}
        if column not in columns:
            connection.execute(f'ALTER TABLE records ADD COLUMN {column} {definition}')

    def add_record(self, record: Record) -> Record:
        artist = record.artist.strip()
        title = record.title.strip()
        if not artist or not title:
            raise ValueError('Artist and title are required')

        values = {
            **record.__dict__,
            'artist': artist,
            'title': title,
            'scanned_at': record.scanned_at or date.today().isoformat(),
        }
        columns = tuple(
            column for column in values
            if column not in {'id', 'updated_at'}
        )
        placeholders = ', '.join('?' for _ in columns)
        assignments = ', '.join(f'{column}=excluded.{column}' for column in columns if column != 'barcode')
        query = f'''
            INSERT INTO records ({', '.join(columns)})
            VALUES ({placeholders})
            ON CONFLICT(barcode) DO UPDATE SET
                {assignments}, updated_at=CURRENT_TIMESTAMP
        ''' if values.get('barcode') else f'''
            INSERT INTO records ({', '.join(columns)})
            VALUES ({placeholders})
        '''

        with self._lock, self.connect() as connection:
            cursor = connection.execute(query, tuple(values[column] for column in columns))
            record_id = cursor.lastrowid
            if values.get('barcode'):
                row = connection.execute(
                    'SELECT * FROM records WHERE barcode = ?', (values['barcode'],)
                ).fetchone()
            else:
                row = connection.execute(
                    'SELECT * FROM records WHERE id = ?', (record_id,)
                ).fetchone()
            return Record.from_row(row)

    def get_record(self, record_id: int) -> Record | None:
        with self._lock, self.connect() as connection:
            row = connection.execute('SELECT * FROM records WHERE id = ?', (record_id,)).fetchone()
        return Record.from_row(row) if row else None

    def update_record(self, record_id: int, changes: dict[str, Any]) -> Record:
        allowed = {
            'barcode', 'discogs_release_id', 'artist', 'title', 'catalog_number',
            'media_type', 'release_year', 'duration', 'purchase_price',
            'discogs_min', 'discogs_median', 'discogs_max', 'price_currency',
            'cover_url', 'cover_cached_path', 'cover_cached_at', 'release_type', 'credits',
        }
        updates = {key: value for key, value in changes.items() if key in allowed}
        if 'artist' in updates:
            updates['artist'] = str(updates['artist'] or '').strip()
        if 'title' in updates:
            updates['title'] = str(updates['title'] or '').strip()
        if not updates:
            record = self.get_record(record_id)
            if not record:
                raise KeyError(f'Record {record_id} does not exist')
            return record
        if not updates.get('artist', True) or not updates.get('title', True):
            raise ValueError('Artist and title cannot be empty')

        assignments = ', '.join(f'{column} = ?' for column in updates)
        values = tuple(updates.values()) + (record_id,)
        with self._lock, self.connect() as connection:
            cursor = connection.execute(
                f'UPDATE records SET {assignments}, updated_at = CURRENT_TIMESTAMP WHERE id = ?',
                values,
            )
            if cursor.rowcount == 0:
                raise KeyError(f'Record {record_id} does not exist')
        return self.get_record(record_id)  # type: ignore[return-value]

    def delete_record(self, record_id: int) -> bool:
        with self._lock, self.connect() as connection:
            cursor = connection.execute('DELETE FROM records WHERE id = ?', (record_id,))
        return cursor.rowcount > 0

    def recent(self, limit: int = 4) -> list[Record]:
        with self._lock, self.connect() as connection:
            rows = connection.execute(
                'SELECT * FROM records ORDER BY scanned_at DESC, id DESC LIMIT ?', (limit,)
            ).fetchall()
        return [Record.from_row(row) for row in rows]

    def search(self, query: str = '', limit: int = 100) -> list[Record]:
        query = query.strip()
        with self._lock, self.connect() as connection:
            if query:
                pattern = f'%{query}%'
                rows = connection.execute(
                    '''SELECT * FROM records
                       WHERE artist LIKE ? COLLATE NOCASE
                          OR title LIKE ? COLLATE NOCASE
                          OR catalog_number LIKE ? COLLATE NOCASE
                          OR barcode LIKE ? COLLATE NOCASE
                       ORDER BY artist COLLATE NOCASE, title COLLATE NOCASE
                       LIMIT ?''',
                    (pattern, pattern, pattern, pattern, limit),
                ).fetchall()
            else:
                rows = connection.execute(
                    'SELECT * FROM records ORDER BY artist COLLATE NOCASE, title COLLATE NOCASE LIMIT ?',
                    (limit,),
                ).fetchall()
        return [Record.from_row(row) for row in rows]

    def by_artist(self, artist: str, limit: int = 100) -> list[Record]:
        with self._lock, self.connect() as connection:
            rows = connection.execute(
                'SELECT * FROM records WHERE artist = ? COLLATE NOCASE ORDER BY title COLLATE NOCASE LIMIT ?',
                (artist.strip(), limit),
            ).fetchall()
        return [Record.from_row(row) for row in rows]

    def statistics(self) -> dict[str, int]:
        with self._lock, self.connect() as connection:
            row = connection.execute('''
                SELECT COUNT(*) AS records,
                       COUNT(DISTINCT artist) AS artists
                FROM records
            ''').fetchone()
            report_count = connection.execute('SELECT COUNT(*) FROM reports').fetchone()[0]
        return {'records': row['records'], 'artists': row['artists'], 'reports': report_count}

    def statistics_detail(self) -> dict[str, list[dict[str, Any]]]:
        with self._lock, self.connect() as connection:
            media_types = connection.execute('''
                SELECT COALESCE(media_type, 'Unknown') AS label, COUNT(*) AS count
                FROM records GROUP BY media_type ORDER BY count DESC, label LIMIT 8
            ''').fetchall()
            years = connection.execute('''
                SELECT COALESCE(CAST(release_year AS TEXT), 'Unknown') AS label, COUNT(*) AS count
                FROM records GROUP BY release_year ORDER BY release_year DESC LIMIT 8
            ''').fetchall()
            artists = connection.execute('''
                SELECT artist AS label, COUNT(*) AS count
                FROM records GROUP BY artist ORDER BY count DESC, label LIMIT 8
            ''').fetchall()
        return {
            'media_types': [dict(row) for row in media_types],
            'years': [dict(row) for row in years],
            'artists': [dict(row) for row in artists],
        }

    def add_report(self, file_path: str | Path, file_format: str, query: str | None, record_count: int) -> Report:
        with self._lock, self.connect() as connection:
            cursor = connection.execute(
                '''INSERT INTO reports (file_path, format, query, record_count)
                   VALUES (?, ?, ?, ?)''',
                (str(file_path), file_format, query, record_count),
            )
            row = connection.execute('SELECT * FROM reports WHERE id = ?', (cursor.lastrowid,)).fetchone()
        return Report(**dict(row))

    def reports(self, limit: int = 20) -> list[Report]:
        with self._lock, self.connect() as connection:
            rows = connection.execute(
                'SELECT * FROM reports ORDER BY created_at DESC, id DESC LIMIT ?', (limit,)
            ).fetchall()
        return [Report(**dict(row)) for row in rows]

    def delete_all(self) -> None:
        with self._lock, self.connect() as connection:
            connection.execute('DELETE FROM records')

    def backup(self, destination: str | Path) -> Path:
        destination_path = Path(destination)
        destination_path.parent.mkdir(parents=True, exist_ok=True)
        with self._lock, self.connect() as source:
            target = sqlite3.connect(destination_path)
            try:
                source.backup(target)
            finally:
                target.close()
        return destination_path


def record_from_payload(payload: dict[str, Any]) -> Record:
    release_year = payload.get('release_year')
    try:
        release_year = int(release_year) if release_year else None
    except (TypeError, ValueError):
        release_year = None
    return Record(
        id=None,
        barcode=payload.get('barcode') or None,
        discogs_release_id=payload.get('discogs_release_id') or None,
        artist=str(payload.get('artist') or '').strip(),
        title=str(payload.get('title') or '').strip(),
        catalog_number=payload.get('catalog_number') or None,
        media_type=payload.get('media_type') or None,
        release_year=release_year,
        duration=payload.get('duration') or None,
        purchase_price=payload.get('purchase_price') or None,
        discogs_min=payload.get('discogs_min') or None,
        discogs_median=payload.get('discogs_median') or None,
        discogs_max=payload.get('discogs_max') or None,
        price_currency=payload.get('price_currency') or None,
        cover_url=payload.get('cover_url') or None,
        cover_cached_path=payload.get('cover_cached_path') or None,
        cover_cached_at=payload.get('cover_cached_at') or None,
        release_type=payload.get('release_type') or None,
        credits=payload.get('credits') or None,
    )
