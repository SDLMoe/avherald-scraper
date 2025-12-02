# -*- coding: utf-8 -*-
"""
This script scrapes incident data from avherald.com.

It includes functions for scraping, parsing, and storing incident data in a SQLite database.

Copyright (C) 2025 by Kolja Nolte
kolja.nolte@gmail.com
https://www.kolja-nolte.com

This work is licensed under the MIT License. You are free to use, share,
and adapt this work, provided that you Include the original copyright notice.

For more information, see the LICENSE file.

Author:    Kolja Nolte
Email:     kolja.nolte@gmail.com
License:   MIT License
Date:      2025
Package:   avherald-scraper
"""

# Import the requests library for making HTTP requests.
import requests

# Import the dotenv library for loading environment variables.
import dotenv

# Import the BeautifulSoup library for parsing HTML.
from bs4 import BeautifulSoup

# Import the regular expression library.
import re

# Import the operating system interface.
import os

# Import the time module.
import time

# Import datetime module.
from datetime import datetime

# Import the URL parsing functions.
from urllib.parse import urljoin

# Import the SQLite library.
import sqlite3

# Import calendar module for UTC timestamp.
import calendar

from requests import Session

from avherald_scraper.aircraft_models import AIRCRAFT_MODEL_NAMES


class AvHeraldAccessError(RuntimeError):
	"""Raised when avherald.com denies access to the headlines."""
	pass

env_path = dotenv.find_dotenv('.env', False)

# if not os.path.exists(env_path):
# 	raise FileNotFoundError(
# 		f"Could not find .env file."
# 		f"Please create one in the root directory based on the .env.example file."
# 	)

# Load environment variables from a .env file.
dotenv.load_dotenv(env_path)

# List of required keys from the .env file
required_keys = [
	"BASE_URL",
	"DATABASE_FILE_PATH"
]

# Check that all required keys are set
missing_keys = [key for key in required_keys if not os.getenv(key)]
if missing_keys:
	raise EnvironmentError(f"Missing required environment variables: {', '.join(missing_keys)}")

# Define the base URL for avherald.com.
BASE_URL = os.getenv("BASE_URL")

# Define the path to the SQLite database file.
DATABASE_FILE_PATH = os.getenv("DATABASE_FILE_PATH")

# Define the regular expression string for matching dates.
DATE_REGEX_STR = r"(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{1,2}(?:st|nd|rd|th)\s+\d{4}"

# Compile the date regular expression.
DATE_REGEX = re.compile(DATE_REGEX_STR)

# Compile the regular expression for removing ordinal suffixes.
ORDINAL_SUFFIX_REGEX = re.compile(r"(?<=\d)(st|nd|rd|th)")

# Regex to detect the location preposition to isolate the aircraft/airline segment.
LOCATION_SPLIT_REGEX = re.compile(
	r'\b(?:at|near|over|enroute to|en route to)\b',
	re.IGNORECASE
)

# Keywords that strongly indicate the beginning of an aircraft description.
AIRCRAFT_KEYWORDS = {
	"aerospatiale",
	"agusta",
	"airbus",
	"airtractor",
	"antonov",
	"atr",
	"avro",
	"bae",
	"beechcraft",
	"bell",
	"boeing",
	"bombardier",
	"britten",
	"caravan",
	"cessna",
	"dash",
	"challenger",
	"cirrus",
	"citation",
	"comac",
	"crj",
	"dassault",
	"diamond",
	"dhc",
	"dornier",
	"douglas",
	"embraer",
	"falcon",
	"fairchild",
	"fokker",
	"gulfstream",
	"helicopter",
	"ilyushin",
	"learjet",
	"let",
	"lockheed",
	"mcdonnell",
	"mitsubishi",
	"mooney",
	"otter",
	"pilatus",
	"piper",
	"robinson",
	"saab",
	"sikorsky",
	"sukhoi",
	"superjet",
	"tecnam",
	"tupolev",
	"ultralight",
	"yakovlev"
}

# Multi-word aircraft descriptors that should be treated as a single unit.
AIRCRAFT_MULTIWORD_PATTERNS = [
	("king", "air"),
	("twin", "otter"),
	("grand", "caravan"),
	("britten", "norman")
]

# Pre-computed lookup of normalized aircraft model names for boundary detection.
_AIRCRAFT_MODEL_LOOKUP = {
	re.sub(r'[^a-z0-9]', '', name.lower()): name for name in AIRCRAFT_MODEL_NAMES
}

# Maximum number of tokens to consider when matching multi-word aircraft names.
_AIRCRAFT_MODEL_MAX_TOKENS = 6

# Words that typically follow the aircraft type and should terminate parsing.
AIRCRAFT_STOPWORDS = {
	"enroute", "en-route", "inflight", "taxi", "taxiing", "departing",
	"departed", "arrival", "arriving", "landing", "takeoff", "take-off",
	"climbed", "descending", "descended", "without", "with", "after",
	"before", "during", "from", "to", "over", "near", "at", "on", "while",
	"when", "and", "due", "because", "following", "shortly", "short",
	"long", "approach", "runway", "stand", "gate"
}

# Regex used to detect conjunctions that may separate multiple aircraft subjects.
SUBJECT_CONJUNCTION_REGEX = re.compile(r'\s+(?:and|&)\s+', re.IGNORECASE)

# Prefix applied to secondary records when a headline describes multiple aircraft.
SECONDARY_TITLE_PREFIX = "[标记"

# Canonical schema definition for the incidents table.
_INCIDENT_TABLE_COLUMNS_SQL = """
        category TEXT,
        title TEXT UNIQUE,
        airline TEXT,
        aircraft TEXT,
        timestamp INTEGER,
        url TEXT
    """

_DESIRED_INCIDENT_COLUMNS = (
	"category",
	"title",
	"airline",
	"aircraft",
	"timestamp",
	"url"
)

# Characters to strip from tokens when trying to identify aircraft boundaries.
_TOKEN_STRIP_CHARS = " ,.;()/[]{}"


def _format_response_preview(response_text, max_lines=5):
	"""
	Returns a preview string containing only the first `max_lines` of the HTTP response.
	"""
	if not response_text:
		return "<empty response>"
	lines = response_text.splitlines()
	preview = "\n".join(lines[:max_lines])
	if len(lines) > max_lines:
		preview += "\n..."
	return preview


def _ensure_not_blocked(response_text):
	"""
	Raises an informative error if the response indicates that the IP is blocked.
	"""
	block_indicators = [
		"Your IP address",
		"has been used for unauthorized accesses",
		"therefore blocked"
	]
	lower_text = response_text.lower()
	if all(phrase.lower() in lower_text for phrase in block_indicators):
		raise AvHeraldAccessError(
			"avherald.com returned an access-block page for this IP. "
			"Please retry from a different network or contact The Aviation Herald."
		)


def _normalize_aircraft_token(token):
	"""
	Normalizes tokens for aircraft detection by stripping punctuation.
	"""
	return token.strip(_TOKEN_STRIP_CHARS)


def _normalize_model_key(text):
	"""
	Produces a comparable key for aircraft model names.
	"""
	return re.sub(r'[^a-z0-9]', '', text.lower())


def _tokens_are_manufacturers(tokens):
	"""
	Checks whether all tokens describe aircraft manufacturers/series.
	"""
	if not tokens:
		return False
	for token in tokens:
		stripped = _normalize_aircraft_token(token).lower()
		if not stripped or stripped not in AIRCRAFT_KEYWORDS:
			return False
	return True


def _token_matches_aircraft(token):
	"""
	Determines whether a token is likely to start an aircraft description.
	"""
	if not token:
		return False
	lower_token = token.lower()
	if lower_token in AIRCRAFT_KEYWORDS:
		return True
	alphanumeric = re.sub(r'[^A-Za-z0-9]', '', token)
	if len(alphanumeric) < 3:
		return False
	return any(char.isalpha() for char in alphanumeric) and any(char.isdigit() for char in alphanumeric)


def _find_aircraft_start_index(raw_tokens, stripped_tokens, lowered_tokens):
	"""
	Finds the index where the aircraft description likely begins.
	"""
	model_index = _find_aircraft_start_by_model(raw_tokens)
	if model_index is not None:
		return model_index
	for pattern in AIRCRAFT_MULTIWORD_PATTERNS:
		size = len(pattern)
		for idx in range(len(lowered_tokens) - size + 1):
			segment = lowered_tokens[idx:idx + size]
			if segment == list(pattern):
				return idx
	for idx, token in enumerate(stripped_tokens):
		if _token_matches_aircraft(token):
			return idx
	return None


def _find_aircraft_start_by_model(raw_tokens):
	"""
	Finds aircraft start index by scanning for known aircraft models.
	"""
	for idx in range(len(raw_tokens)):
		if _match_known_aircraft_tokens(raw_tokens[idx:]):
			return idx
	return None


def _match_known_aircraft_tokens(raw_tokens):
	"""
	Returns the slice of tokens that matches a known aircraft model.
	"""
	sanitized_tokens = [_normalize_aircraft_token(token) for token in raw_tokens]
	max_len = min(len(sanitized_tokens), _AIRCRAFT_MODEL_MAX_TOKENS)
	for length in range(max_len, 0, -1):
		segment = sanitized_tokens[:length]
		if not all(segment):
			continue
		key = _normalize_model_key(" ".join(segment))
		if key in _AIRCRAFT_MODEL_LOOKUP:
			return raw_tokens[:length]
	return None


def _trim_aircraft_tokens(raw_tokens):
	"""
	Removes trailing descriptive words from the aircraft token list.
	"""
	if not raw_tokens:
		return raw_tokens
	known_match = _match_known_aircraft_tokens(raw_tokens)
	if known_match:
		return known_match
	trimmed = []
	for token in raw_tokens:
		stripped = _normalize_aircraft_token(token)
		lowered = stripped.lower()
		if stripped and lowered in AIRCRAFT_STOPWORDS and trimmed:
			break
		trimmed.append(token)
	return trimmed if trimmed else raw_tokens


def _split_subject_chunks(subject):
	"""
	Splits a subject string into chunks delimited by conjunctions like 'and' or '&'.
	"""
	if not subject:
		return []
	chunks = SUBJECT_CONJUNCTION_REGEX.split(subject)
	return [chunk.strip(" ,;/") for chunk in chunks if chunk and chunk.strip(" ,;/")]


def _parse_subject_chunk(chunk):
	"""
	Parses a single subject chunk into airline and aircraft strings.
	"""
	raw_tokens = chunk.split()
	if not raw_tokens:
		return "Unknown", "Unknown"
	stripped_tokens = [_normalize_aircraft_token(token) for token in raw_tokens]
	lowered_tokens = [token.lower() for token in stripped_tokens]
	aircraft_start = _find_aircraft_start_index(raw_tokens, stripped_tokens, lowered_tokens)
	if aircraft_start is None:
		return "Unknown", chunk.strip()
	airline_tokens = raw_tokens[:aircraft_start]
	manufacturer_prefix = _tokens_are_manufacturers(airline_tokens)
	aircraft_tokens = raw_tokens[aircraft_start:]
	if manufacturer_prefix:
		airline = "Unknown"
		aircraft_tokens = airline_tokens + aircraft_tokens
		numeric_prefix_tokens = []
	else:
		alpha_tokens = [token for token in airline_tokens if any(char.isalpha() for char in token)]
		airline = " ".join(alpha_tokens).strip()
		numeric_prefix_tokens = []
		if not airline:
			airline = "Unknown"
			numeric_prefix_tokens = [token for token in airline_tokens if not any(char.isalpha() for char in token)]
		if numeric_prefix_tokens:
			aircraft_tokens = numeric_prefix_tokens + aircraft_tokens
	aircraft_tokens = _trim_aircraft_tokens(aircraft_tokens)
	aircraft = " ".join(token for token in aircraft_tokens).strip(" ,.;") or "Unknown"
	return airline, aircraft


def _chunks_are_valid(parsed_chunks):
	"""
	Determines whether the parsed chunks represent distinct, valid aircraft entries.
	"""
	if len(parsed_chunks) < 2:
		return False
	return all(aircraft != "Unknown" for _, aircraft in parsed_chunks)


def _extract_subject_segment(clean_title):
	"""
	Returns the portion of the cleaned title that precedes the location indicator.
	"""
	if not clean_title:
		return ""
	match = LOCATION_SPLIT_REGEX.search(clean_title)
	if match:
		return clean_title[:match.start()].strip()
	return clean_title.strip()


def _extract_aircraft_entries(clean_title):
	"""
	Returns a list of (airline, aircraft) tuples from the cleaned incident title.
	"""
	subject = _extract_subject_segment(clean_title)
	if not subject:
		return [("Unknown", "Unknown")]
	chunks = _split_subject_chunks(subject)
	if chunks:
		parsed_chunks = [_parse_subject_chunk(chunk) for chunk in chunks]
		if _chunks_are_valid(parsed_chunks):
			return parsed_chunks
	# Fallback to parsing the entire subject as a single chunk.
	return [_parse_subject_chunk(subject or clean_title)]


def _build_variant_title(original_title, airline, variant_index):
	"""
	Builds a title for secondary entries to keep database titles unique.
	"""
	if variant_index == 0:
		return original_title
	suffix = airline if airline != "Unknown" else f"#{variant_index + 1}"
	return f"{SECONDARY_TITLE_PREFIX} {suffix}] {original_title}"


def _get_incident_columns(conn):
	"""
	Returns the current column order for the incidents table.
	"""
	result = conn.execute("PRAGMA table_info(incidents);")
	return [row[1] for row in result.fetchall()]


def _has_desired_incident_schema(columns):
	"""
	Determines if the incidents table already matches the desired schema.
	"""
	desired = list(_DESIRED_INCIDENT_COLUMNS)
	if not columns:
		return False
	if columns == desired:
		return True
	return len(columns) == len(desired) and set(columns) == set(desired)


def _ensure_latest_schema(conn):
	"""
	Ensures the incidents table contains only the desired columns.
	"""
	columns = _get_incident_columns(conn)
	if not columns:
		return
	if _has_desired_incident_schema(columns):
		return
	_migrate_incidents_table(conn, columns)


def _migrate_incidents_table(conn, existing_columns):
	"""
	Rebuilds the incidents table to match the desired schema while preserving data.
	"""
	temp_table = "incidents_legacy"
	conn.execute(f"ALTER TABLE incidents RENAME TO {temp_table};")
	conn.execute(f"""
        CREATE TABLE incidents (
{_INCIDENT_TABLE_COLUMNS_SQL}
        );
    """)
	columns_to_copy = [col for col in _DESIRED_INCIDENT_COLUMNS if col in existing_columns]
	if columns_to_copy:
		column_csv = ", ".join(columns_to_copy)
		conn.execute(
			f"INSERT INTO incidents ({column_csv}) SELECT {column_csv} FROM {temp_table};"
		)
	conn.execute(f"DROP TABLE {temp_table};")
	conn.commit()


# Create the output directory from the database file path.
output_directory = os.path.dirname(DATABASE_FILE_PATH)

# Check if the output directory exists.
if not os.path.isdir(output_directory):
	# Create the output directory if it doesn't exist, allowing intermediate directories to be created.
	os.makedirs(output_directory, exist_ok=True)


#
# Converts a date string (e.g. 'Mar 31st 2025') into a UNIX timestamp.
#
# @param date_string The date string to convert.
# @param show_details Whether to print details if parsing fails.
# @return The UNIX timestamp or None if parsing fails.
def date_to_timestamp(date_string, show_details=False):
	# Check if the date string is empty.
	if not date_string:
		# Return None if the date string is empty.
		return None
	# Remove ordinal suffixes from the date string.
	cleaned_date_string = ORDINAL_SUFFIX_REGEX.sub("", date_string)
	# Try to convert the cleaned date string to a timestamp.
	try:
		# Parse the cleaned date string into a datetime object.
		dt_object = datetime.strptime(cleaned_date_string, "%b %d %Y")
		# Convert the datetime object to a UNIX timestamp and return it.
		return calendar.timegm(dt_object.timetuple())
	# Catch a ValueError if the date string cannot be parsed.
	except ValueError:
		# Check if details should be shown.
		if show_details:
			# Print a warning message if the date string could not be parsed.
			print(f"Warning: Could not parse date string: '{date_string}'")
		# Return None if parsing fails.
		return None


#
# Processes the original title string.
#
# @param original_title The original title string to process.
# @param show_details Whether to print details if parsing fails.
# @return A dict with keys: 'title', 'timestamp', 'airline', 'aircraft'
def process_title(original_title, show_details=False):
	# Strip leading/trailing whitespace from the title.
	title = original_title.strip()

	# Remove any trailing descriptive clauses (often after the first comma).
	if ',' in title:
		title_for_parsing = title.split(',', 1)[0].strip()
	else:
		title_for_parsing = title

	# Search for a date in the title.
	date_match = DATE_REGEX.search(title_for_parsing)
	# Check if a date was found.
	if date_match:
		# Extract the date string.
		date_str = date_match.group(0)
		# Convert the date string to a timestamp.
		timestamp = date_to_timestamp(date_str, show_details=show_details)
		# Create a date segment string to remove from the title.
		date_segment = " on " + date_str
		# Remove the date segment from the title.
		title_for_parsing = title_for_parsing.replace(date_segment, "").strip()
	# If no date was found.
	else:
		# Set the timestamp to None.
		timestamp = None

	entries = []
	pairs = _extract_aircraft_entries(title_for_parsing)
	for idx, (airline, aircraft) in enumerate(pairs):
		entry_title = _build_variant_title(title, airline, idx)
		entries.append({
			'title': entry_title,
			'timestamp': timestamp,
			'airline': airline,
			'aircraft': aircraft
		})
	return entries


#
# Scrapes a single page of avherald.com incidents.
#
# @param page_url The URL of the page to scrape.
# @param show_details Whether to print details during scraping.
# @return A tuple: (list_of_incidents_on_page, next_page_url or None)
def scrape_single_page(page_url, show_details=False):
	# Check if details should be shown.
	if show_details:
		# Print the URL being scraped.
		print(f"Attempting to scrape: {page_url}")

	# Remove or keep proxy settings commented as not in use
	# username = "fiPGJc7Sg"
	# password = "01GDK78135NM0F00KS5RV5TSYX"
	# proxy_host = "hk-hkg01-ike.provpn.world"
	# proxies = { ... }

	session = requests.Session()
	session.trust_env = False  # Ensure system proxies are ignored

	# Add realistic headers to mimic a browser
	headers = {
		"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.5845.188 Safari/537.36"
	}

	try:
		response = session.get(page_url, headers=headers, timeout=10)
		response.raise_for_status()
	except requests.exceptions.Timeout:
		if show_details:
			print(f"Error: Request timed out for {page_url}. Skipping this page.")
		return [], None
	except requests.exceptions.RequestException as e:
		if show_details:
			print(f"Error fetching URL {page_url}: {e}. Skipping this page.")
		else:
			print(f"Error fetching URL {page_url}: {e}")
		return [], None

	html_text = response.text
	if show_details:
		preview = _format_response_preview(html_text, max_lines=5)
		print("Response received (first 5 lines):\n" + preview)
	_ensure_not_blocked(html_text)

	# Check if details should be shown.
	if show_details:
		# Print a message indicating that the page content was successfully fetched.
		print("Successfully fetched page content. Parsing HTML...")
	# Parse the HTML content using BeautifulSoup.
	soup = BeautifulSoup(html_text, 'lxml')
	# Initialize an empty list to store incidents found on the page.
	page_incidents = []
	# Find all headline spans on the page.
	headline_spans = soup.find_all('span', class_='headline_avherald')

	# Check if details should be shown.
	if show_details:
		# Print the number of potential headline spans found.
		print(f"Found {len(headline_spans)} potential headline spans on this page.")

	# Check if no headline spans were found.
	if not headline_spans:
		# Check if details should be shown.
		if show_details:
			# Print a warning message if no headline spans were found.
			print("Warning: No headline spans found on this page.")
	# If headline spans were found.
	else:
		# Iterate over each headline span.
		for headline_span in headline_spans:
			# Find the parent <a> tag of the headline span.
			link_tag = headline_span.find_parent('a')
			# Check if the <a> tag exists and has an 'href' attribute.
			if not link_tag or not link_tag.has_attr('href'):
				# Skip to the next iteration if the <a> tag is missing or invalid.
				continue

			# Find the parent <tr> tag of the link tag.
			parent_row = link_tag.find_parent('tr')
			# Initialize the category to "Unknown".
			category = "Unknown"
			# Check if the parent row exists.
			if parent_row:
				# Find the <img> tag within the parent row.
				icon_tag = parent_row.find('img')
				# Check if the <img> tag exists and has a 'src' attribute.
				if icon_tag and icon_tag.has_attr('src'):
					# Extract the filename from the 'src' attribute.
					filename = os.path.basename(icon_tag['src'])
					# Check if the filename ends with '.gif' (case-insensitive).
					if filename.lower().endswith('.gif'):
						# Set the category to the filename without the '.gif' extension.
						category = filename[:-4]
					# Otherwise.
					else:
						# Set the category to the filename.
						category = filename
			# Extract the original title from the headline span and strip whitespace.
			original_title = headline_span.text.strip()
			# Process the title to extract relevant information.
			parsed_entries = process_title(original_title, show_details=show_details)

			# Extract the relative URL from the <a> tag.
			relative_url = link_tag['href']
			# Create the absolute URL by joining the base URL and the relative URL.
			absolute_url = urljoin(BASE_URL, relative_url)

			for entry in parsed_entries:
				incident = {
					'category': category,
					'title': entry['title'],
					'airline': entry['airline'],
					'aircraft': entry['aircraft'],
					'timestamp': entry['timestamp'],
					'url': absolute_url
				}
				# Add the incident dictionary to the list of page incidents.
				page_incidents.append(incident)

	# Initialize the next page URL to None.
	next_page_url = None
	# Find the next page link.
	next_link_tag = soup.select_one('a:has(img[src$="next.jpg"])')
	# Check if the next page link exists and has an 'href' attribute.
	if next_link_tag and next_link_tag.has_attr('href'):
		# Extract the relative URL from the next page link.
		relative_next_url = next_link_tag['href']
		# Create the absolute URL for the next page.
		next_page_url = urljoin(BASE_URL, relative_next_url)
		# Check if details should be shown.
		if show_details:
			# Print the next page URL.
			print(f"Found next page link: {next_page_url}")
	# If no next page link was found.
	else:
		# Check if details should be shown.
		if show_details:
			# Print a message indicating that no next page link was found.
			print("No 'next.jpg' link found on this page.")

	# Return the list of incidents and the next page URL.
	return page_incidents, next_page_url


#
# Creates the 'incidents' table with the appropriate columns if it doesn't exist.
#
# @param conn The database connection object.
def create_table_if_not_exists(conn):
	# Define the SQL query to create the 'incidents' table if it doesn't exist.
	sql = f"""
    CREATE TABLE IF NOT EXISTS incidents (
{_INCIDENT_TABLE_COLUMNS_SQL}
    );
    """
	# Execute the SQL query.
	conn.execute(sql)
	# Commit the changes to the database.
	conn.commit()
	_ensure_latest_schema(conn)


#
# Insert an incident into the database.
#
# @param conn The database connection object.
# @param incident The incident data to insert.
# @return True if a row was inserted, False otherwise.
def insert_incident(conn, incident):
	# Skip incidents with the category "news"
	if incident['category'].lower() == "news":
		# Returns False if the category is new.
		return False

	# Define the SQL query to insert an incident into the database, ignoring duplicates.
	sql = """
    INSERT OR IGNORE INTO incidents (category, title, airline, aircraft, timestamp, url)
    VALUES (?, ?, ?, ?, ?, ?);
    """
	# Execute the SQL query with the incident data.
	cur = conn.execute(
		sql, (
			incident['category'],
			incident['title'],
			incident['airline'],
			incident['aircraft'],
			incident['timestamp'],
			incident['url']
		)
	)
	# Commit the changes to the database.
	conn.commit()
	# Return True if a row was inserted, False otherwise.
	return cur.rowcount == 1  # True if inserted, False if skipped


#
# Inserts a list of incidents into the database.
#
# @param conn The database connection object.
# @param incidents A list of incident dictionaries to insert.
# @return A tuple: (inserted_count, skipped_count)
def insert_incidents(conn, incidents):
	# Initialize the inserted count.
	inserted = 0
	# Initialize the skipped count.
	skipped = 0
	# Iterate over each incident in the list.
	for incident in incidents:
		# Insert the incident into the database.
		if insert_incident(conn, incident):
			# Increment the inserted count if the incident was inserted.
			inserted += 1
		# If the incident was skipped.
		else:
			# Increment the skipped count if the incident was skipped.
			skipped += 1
	# Return the inserted and skipped counts.
	return inserted, skipped


#
# Scrapes avherald.com for incident data and stores it in a database.
#
# @param max_pages_to_scrape The maximum number of pages to scrape.
# @param request_delay_seconds The delay in seconds between requests.
# @param database_file The path to the SQLite database file.
# @param show_details Whether to print details during scraping.
def scrape(max_pages_to_scrape=3, request_delay_seconds=3, show_details=True):
	# Connect to the SQLite database.
	conn = sqlite3.connect(DATABASE_FILE_PATH)
	# Create the 'incidents' table if it doesn't exist.
	create_table_if_not_exists(conn)
	# Set the initial URL to the base URL.
	current_url = BASE_URL
	# Initialize the pages scraped count.
	pages_scraped = 0

	# Loop while the number of pages scraped is less than the maximum and the current URL is not None.
	while pages_scraped < max_pages_to_scrape and current_url:
		# Check if details should be shown.
		if show_details:
			# Print the current page being scraped.
			print(f"\n--- Scraping Page {pages_scraped + 1} ---")
		# Scrape the current page.
		incidents_on_page, next_url = scrape_single_page(current_url, show_details=show_details)
		# Check if any incidents were found on the page.
		if incidents_on_page:
			# Insert the incidents into the database.
			inserted, skipped = insert_incidents(conn, incidents_on_page)
			# Check if details should be shown.
			if show_details:
				# Print the number of incidents inserted and skipped.
				print(f"Inserted {inserted} incidents from this page into the database.")
				print(f"Skipped {skipped} incidents (already in database).")
		# If no incidents were found on the page.
		else:
			# Check if details should be shown.
			if show_details:
				# Print a message indicating that no incidents were inserted.
				print("No incidents inserted from this page.")
		# Increment the pages scraped count.
		pages_scraped += 1
		# Set the current URL to the next URL.
		current_url = next_url
		# Check if there is a next URL and the number of pages scraped is less than the maximum.
		if current_url and pages_scraped < max_pages_to_scrape:
			# Check if details should be shown.
			if show_details:
				# Print a message indicating that the script is pausing.
				print(f"Pausing for {request_delay_seconds} second(s)...")
			# Pause for the specified delay.
			time.sleep(request_delay_seconds)
	# Close the database connection.
	conn.close()
	# Check if details should be shown.
	if show_details:
		# Print a message indicating that scraping is finished.
		print(f"\n--- Finished Scraping ---")
		# Print the total number of pages scraped.
		print(f"Scraped a total of {pages_scraped} pages and stored new incidents into {DATABASE_FILE_PATH}.")
