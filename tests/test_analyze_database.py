import sqlite3

import pytest

from analyze_database import analyze_database, fetch_counts


def _prepare_db(tmp_path):
	db_file = tmp_path / "data.sqlite"
	conn = sqlite3.connect(db_file)
	conn.execute("""
        CREATE TABLE incidents (
            category TEXT,
            title TEXT UNIQUE,
            airline TEXT,
            aircraft TEXT,
            timestamp INTEGER,
            url TEXT
        );
    """)
	entries = [
		("incident", "T1", "Airline A", "A320", 1, "http://a"),
		("incident", "T2", "Airline A", "B738", 2, "http://b"),
		("incident", "T3", "Airline B", "A320", 3, "http://c"),
		("incident", "T4", "Airline B", "B738", 4, "http://d"),
		("incident", "T5", "Airline C", "B738", 5, "http://e"),
	]
	conn.executemany("INSERT INTO incidents VALUES (?, ?, ?, ?, ?, ?);", entries)
	conn.commit()
	return conn, str(db_file)


def test_fetch_counts_groups_data(tmp_path):
	conn, _ = _prepare_db(tmp_path)
	with conn:
		airline_counts = fetch_counts(conn, "airline")
		aircraft_counts = fetch_counts(conn, "aircraft")
	assert airline_counts[0] == ("Airline A", 2)
	assert airline_counts[1] == ("Airline B", 2)
	assert aircraft_counts[0] == ("B738", 3)
	assert aircraft_counts[1] == ("A320", 2)


def test_analyze_database_prints_sorted_output(tmp_path, capsys):
	conn, db_path = _prepare_db(tmp_path)
	conn.close()
	analyze_database(db_path, mode="aircraft", limit=2)
	captured = capsys.readouterr().out
	assert "按机型统计" in captured
	assert "B738 3次" in captured
	assert "A320 2次" in captured

