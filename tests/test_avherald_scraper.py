import pytest

import avherald_scraper.avherald_scraper as avherald_scraper


# Defines the test case for the date_to_timestamp function with valid input.
def test_date_to_timestamp_valid():
	# Asserts that the date "Mar 31st 2025" is correctly converted to its timestamp.
	assert avherald_scraper.date_to_timestamp("Mar 31st 2025") == 1743379200
	# Asserts that the date "Jan 1st 2020" is correctly converted to its timestamp.
	assert avherald_scraper.date_to_timestamp("Jan 1st 2020") == 1577836800


# Defines the test case for the date_to_timestamp function with invalid input.
def test_date_to_timestamp_invalid():
	# Asserts that an empty string input to date_to_timestamp returns None.
	assert avherald_scraper.date_to_timestamp("") is None
	# Asserts that an invalid date string input to date_to_timestamp returns None.
	assert avherald_scraper.date_to_timestamp("Not a date") is None


# Defines a test case for process_title when all fields are present.
def test_process_title_with_all_fields():
	# Defines a title string with all fields present.
	title = "Boeing 737 at Berlin on Mar 31st 2025, engine failure"
	# Processes the title string using the process_title function.
	results = avherald_scraper.process_title(title)
	assert len(results) == 1
	result = results[0]
	# Asserts that the stored title remains unchanged.
	assert result['title'] == "Boeing 737 at Berlin on Mar 31st 2025, engine failure"
	# Asserts that the timestamp is extracted and converted correctly.
	assert result['timestamp'] == 1743379200
	# Asserts that airline/aircraft defaults are set.
	assert result['airline'] == "Unknown"
	assert result['aircraft'] == "Boeing 737"


# Ensures airline and aircraft information can be extracted.
def test_process_title_extracts_airline_and_aircraft():
	title = "Ryanair B738 at Dublin on Mar 31st 2025, tail strike"
	results = avherald_scraper.process_title(title)
	result = results[0]
	assert result['airline'] == "Ryanair"
	assert result['aircraft'] == "B738"


def test_process_title_airline_followed_by_model():
	title1 = "Jet2 B738 at Bristol on Nov 11th 2025, wing tip strike on go around"
	title2 = "Cityjet CRJX at Frankfurt on Sep 28th 2025, smoke on board"
	result1 = avherald_scraper.process_title(title1)[0]
	result2 = avherald_scraper.process_title(title2)[0]
	assert result1['airline'] == "Jet2"
	assert result1['aircraft'] == "B738"
	assert result2['airline'] == "Cityjet"
	assert result2['aircraft'] == "CRJX"


# Ensures multi-aircraft headlines are split into separate entries.
def test_process_title_splits_multiple_aircraft():
	title = "Canada BCS3 and United B38M at San Francisco on Jun 24th 2025, ATC operational error"
	results = avherald_scraper.process_title(title)
	assert len(results) == 2
	assert results[0]['airline'] == "Canada"
	assert results[0]['aircraft'] == "BCS3"
	assert results[0]['title'] == title
	assert results[1]['airline'] == "United"
	assert results[1]['aircraft'] == "B38M"
	assert results[1]['title'].startswith("[标记")
	assert title in results[1]['title']


# Defines a test case for process_title without explicit location keywords.
def test_process_title_without_location_keywords():
	# Defines a title string without location.
	title = "Airbus A320 on Mar 31st 2025, bird strike"
	# Processes the title string using the process_title function.
	result = avherald_scraper.process_title(title)[0]
	# Asserts that the airline falls back to Unknown when none is given.
	assert result['airline'] == "Unknown"
	# Asserts that the aircraft is still captured.
	assert result['aircraft'] == "Airbus A320"


# Ensures trailing descriptive words are trimmed from the aircraft type.
def test_process_title_cleans_trailing_aircraft_words():
	title = "THY A332 enroute on Aug 31st 2025, climbed without clearance, loss of separation"
	result = avherald_scraper.process_title(title)[0]
	assert result['airline'] == "THY"
	assert result['aircraft'] == "A332"


# Defines a test case for process_title when the date is missing.
def test_process_title_without_date():
	# Defines a title string without date.
	title = "Piper PA-28 at London, gear up landing"
	# Processes the title string using the process_title function.
	result = avherald_scraper.process_title(title)[0]
	# Asserts that the timestamp is None when the date is missing.
	assert result['timestamp'] is None
	# Asserts that the aircraft is captured.
	assert result['aircraft'] == "Piper PA-28"


# Defines a test case for process_title with minimal information.
def test_process_title_minimal():
	# Defines a minimal title string.
	title = "Unknown incident"
	# Processes the title string using the process_title function.
	result = avherald_scraper.process_title(title)[0]
	# Asserts that the timestamp is None when the title is minimal.
	assert result['timestamp'] is None
	# Asserts that both airline and aircraft default to Unknown text.
	assert result['airline'] == "Unknown"
	assert result['aircraft'] == "Unknown incident"


# Defines a test case for insert_incident and insert_incidents functions.
def test_insert_incident_and_insert_incidents(tmp_path):
	# Creates a temporary database file path using tmp_path fixture.
	db_file = tmp_path / "test.sqlite"
	# Connects to the SQLite database.
	conn = avherald_scraper.sqlite3.connect(str(db_file))
	# Creates the incident table if it doesn't exist.
	avherald_scraper.create_table_if_not_exists(conn)
	# Defines a sample incident dictionary.
	incident = {
		# Defines the category of the incident.
		'category':  'incident',
		# Defines the title of the incident.
		'title':     'Test Title',
		# Defines the airline storing information.
		'airline':   'Test Airline',
		# Defines the aircraft storing information.
		'aircraft':  'Test Aircraft',
		# Defines the timestamp of the incident.
		'timestamp': 1234567890,
		# Defines the URL of the incident.
		'url':       'http://example.com'
	}
	# Asserts that the first insertion of the incident is successful (returns True).
	assert avherald_scraper.insert_incident(conn, incident) is True
	# Asserts that a duplicate insertion of the incident is skipped (returns False).
	assert avherald_scraper.insert_incident(conn, incident) is False
	# Defines a list of incidents to be inserted.
	incidents = [incident, dict(incident, title='Test Title 2')]
	# Inserts the list of incidents into the database.
	inserted, skipped = avherald_scraper.insert_incidents(conn, incidents)
	# Asserts that one incident was inserted.
	assert inserted == 1
	# Asserts that one incident was skipped.
	assert skipped == 1
	# Closes the database connection.
	conn.close()


# Defines a test case for scrape_single_page function.
def test_scrape_single_page(monkeypatch):
	# Defines a mock HTML content for testing.
	html = """
    <html>
    <body>
        <table>
            <tr>
                <td><img src="incident.gif"></td>
                <td>
                    <a href="/article1">
                        <span class="headline_avherald">Boeing 737 at Berlin on Mar 31st 2025, engine failure</span>
                    </a>
                </td>
            </tr>
        </table>
        <a href="/nextpage"><img src="next.jpg"></a>
    </body>
    </html>
    """

	# Defines a mock response class for simulating HTTP responses.
	class MockResponse:
		# Initializes the MockResponse object with text, status code, and encoding.
		def __init__(self, text):
			# Sets the text of the response.
			self.text = text
			# Sets the status code of the response.
			self.status_code = 200
			# Sets the encoding of the response.
			self.encoding = 'utf-8'

		# Defines a mock method to simulate raising an exception for bad status codes.
		def raise_for_status(self): pass

	# Defines a mock session for simulating HTTP GET requests.
	class MockSession:
		def __init__(self):
			self.trust_env = True

		def get(self, *args, **kwargs):
			return MockResponse(html)

	# Uses monkeypatch to replace the requests.Session class with MockSession.
	monkeypatch.setattr(avherald_scraper.requests, "Session", MockSession)
	# Scrapes a single page using the mock HTTP response.
	incidents, next_url = avherald_scraper.scrape_single_page("http://fakeurl", show_details=False)
	# Asserts that the number of incidents scraped is 1.
	assert len(incidents) == 1
	# Asserts that the title of the scraped incident is preserved.
	assert incidents[0]['title'] == "Boeing 737 at Berlin on Mar 31st 2025, engine failure"
	# Asserts airline/aircraft parsing values.
	assert incidents[0]['airline'] == "Unknown"
	assert incidents[0]['aircraft'] == "Boeing 737"
	# Asserts that the next URL extracted is correct.
	assert next_url.endswith("/nextpage")


def test_scrape_single_page_multiple_entries(monkeypatch):
	html = """
    <html>
    <body>
        <table>
            <tr>
                <td><img src="incident.gif"></td>
                <td>
                    <a href="/article1">
                        <span class="headline_avherald">Canada BCS3 and United B38M at San Francisco on Jun 24th 2025, ATC operational error</span>
                    </a>
                </td>
            </tr>
        </table>
    </body>
    </html>
    """

	class MockResponse:
		def __init__(self, text):
			self.text = text
			self.status_code = 200

		def raise_for_status(self):
			return None

	class MockSession:
		def __init__(self):
			self.trust_env = True

		def get(self, *args, **kwargs):
			return MockResponse(html)

	monkeypatch.setattr(avherald_scraper.requests, "Session", MockSession)

	incidents, next_url = avherald_scraper.scrape_single_page("http://fakeurl", show_details=False)
	assert len(incidents) == 2
	assert incidents[0]['airline'] == "Canada"
	assert incidents[0]['aircraft'] == "BCS3"
	assert incidents[1]['airline'] == "United"
	assert incidents[1]['aircraft'] == "B38M"
	assert incidents[1]['title'].startswith("[标记")
	assert incidents[0]['title'].endswith("ATC operational error")
	assert next_url is None


def test_scrape_single_page_detects_ip_block(monkeypatch):
	html = "<html><body><p>Your IP address 1.2.3.4 has been used for unauthorized accesses and is therefore blocked!</p></body></html>"

	class MockResponse:
		def __init__(self, text):
			self.text = text
			self.status_code = 200

		def raise_for_status(self):
			return None

	class MockSession:
		def __init__(self):
			self.trust_env = True

		def get(self, *args, **kwargs):
			return MockResponse(html)

	monkeypatch.setattr(avherald_scraper.requests, "Session", MockSession)

	with pytest.raises(avherald_scraper.AvHeraldAccessError):
		avherald_scraper.scrape_single_page("http://fakeurl", show_details=False)
