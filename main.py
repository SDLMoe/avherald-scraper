# -*- coding: utf-8 -*-

# Copyright (C) 2025 by Kolja Nolte
# kolja.nolte@gmail.com
# https://wwww.kolja-nolte.com
#
# This script scrapes incident data from avherald.com.
# Please read the README.md for more information.
#
# This work is licensed under the MIT License. You are free to use, share,
# and adapt this work, provided that you Include the original copyright notice.
#
# For more information, see the LICENSE file.
#
# Author:    Kolja Nolte
# Email:     kolja.nolte@email.com
# License:   MIT License
# Date:      2025
# Package:   avherald-scraper

"""
Module Docstring: main.py

This script serves as the entry point for scraping aviation accident data from AV Herald.
It configures and initiates the scraping process, allowing users to specify parameters
such as the maximum number of pages to scrape, the delay between requests, the database
file for storing the scraped data, and whether to display detailed output during the scraping.
"""

# Import standard library modules
import os

# Import the avherald_scraper module
from avherald_scraper import avherald_scraper
import dotenv

# Default configuration values (used if the environment does not override them)
DEFAULT_MAX_PAGES_TO_SCRAPE = 20
DEFAULT_REQUEST_DELAY_SECONDS = 3
DEFAULT_SHOW_DETAILS = True


def _load_int_from_env(env_key, default):
	"""
	Returns an integer pulled from the environment or the provided default.
	"""
	value = os.getenv(env_key)
	if value is None:
		return default
	try:
		return int(value)
	except ValueError:
		print(f"Warning: Invalid integer for {env_key}='{value}'. Falling back to {default}.")
		return default


def _load_bool_from_env(env_key, default):
	"""
	Returns a boolean pulled from the environment or the provided default.
	"""
	value = os.getenv(env_key)
	if value is None:
		return default
	lower_value = value.strip().lower()
	if lower_value in {"1", "true", "yes", "on"}:
		return True
	if lower_value in {"0", "false", "no", "off"}:
		return False
	print(f"Warning: Invalid boolean for {env_key}='{value}'. Falling back to {default}.")
	return default


def _build_scrape_kwargs():
	"""
	Computes the keyword arguments for avherald_scraper.scrape() using env overrides.
	"""
	env_path = dotenv.find_dotenv('.env', False)
	dotenv.load_dotenv(env_path)
	return {
		"max_pages_to_scrape": _load_int_from_env("MAX_PAGES_TO_SCRAPE", DEFAULT_MAX_PAGES_TO_SCRAPE),
		"request_delay_seconds": _load_int_from_env("REQUEST_DELAY_SECONDS", DEFAULT_REQUEST_DELAY_SECONDS),
		"show_details": _load_bool_from_env("SHOW_DETAILS", DEFAULT_SHOW_DETAILS)
	}


def main():
	"""
	Function Docstring: main()

	This function orchestrates the scraping process by calling the scrape function
	from the avherald_scraper module with specified configuration parameters.
	"""

	# Call the scrape function with computed parameters
	avherald_scraper.scrape(**_build_scrape_kwargs())


# Check if the script is being run as the main module
if __name__ == "__main__":
	# Call the main function to start the scraping process
	main()
