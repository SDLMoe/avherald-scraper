import main


def _noop(*args, **kwargs):
	return None


def test_build_scrape_kwargs_reads_environment(monkeypatch):
	monkeypatch.setenv("MAX_PAGES_TO_SCRAPE", "5")
	monkeypatch.setenv("REQUEST_DELAY_SECONDS", "10")
	monkeypatch.setenv("SHOW_DETAILS", "false")
	monkeypatch.setattr(main.dotenv, "load_dotenv", _noop)

	config = main._build_scrape_kwargs()

	assert config["max_pages_to_scrape"] == 5
	assert config["request_delay_seconds"] == 10
	assert config["show_details"] is False


def test_build_scrape_kwargs_invalid_values(monkeypatch):
	monkeypatch.setenv("MAX_PAGES_TO_SCRAPE", "invalid")
	monkeypatch.setenv("REQUEST_DELAY_SECONDS", "invalid")
	monkeypatch.setenv("SHOW_DETAILS", "maybe")
	monkeypatch.setattr(main.dotenv, "load_dotenv", _noop)

	config = main._build_scrape_kwargs()

	assert config["max_pages_to_scrape"] == main.DEFAULT_MAX_PAGES_TO_SCRAPE
	assert config["request_delay_seconds"] == main.DEFAULT_REQUEST_DELAY_SECONDS
	assert config["show_details"] == main.DEFAULT_SHOW_DETAILS

