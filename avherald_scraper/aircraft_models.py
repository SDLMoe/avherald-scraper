"""
Catalog of common aircraft designations that appear on avherald.com headlines.
The list combines ICAO/IATA short codes (e.g., A332, B738), marketing names
(e.g., A320neo, Boeing 747-8) and frequently used abbreviations. The scraper
uses this catalog to keep the extracted aircraft type clean by trimming any
trailing descriptive words once a known model has been detected.
"""

# The list is intentionally redundant (e.g., "A320" and "A320neo") so that the
# parser can match the exact spelling found in the headline. Keep entries in
# ASCII and upper-case for readability; matching is case-insensitive.
AIRCRAFT_MODEL_NAMES = [
	# Airbus narrow-body
	"A318", "A319", "A319neo", "A320", "A320neo", "A321", "A321neo",
	"A20N", "A21N", "A220", "A220-100", "A220-300", "A221", "A223",
	# Airbus wide-body
	"A300", "A300-600", "A306", "A310", "A330", "A330-200", "A330-300",
	"A330-800", "A330-900", "A332", "A333", "A338", "A339",
	"A340", "A340-200", "A340-300", "A340-500", "A340-600",
	"A342", "A343", "A345", "A346",
	"A350", "A350-900", "A350-1000", "A359", "A35K",
	"A380", "A380-800", "A388",
	# Boeing narrow-body
	"B707", "B712", "B717", "B720", "B721", "B722", "B727",
	"B731", "B732", "B733", "B734", "B735", "B736", "B737",
	"B737-200", "B737-300", "B737-400", "B737-500", "B737-600",
	"B737-700", "B737-800", "B737-900",
	"B738", "B739", "B73H", "B73M", "B37M", "B38M", "B39M",
	# Boeing wide-body
	"B741", "B742", "B743", "B744", "B747-200", "B747-300", "B747-400",
	"B747-8", "B748",
	"B752", "B753", "B757-200", "B757-300",
	"B762", "B763", "B764", "B767-200", "B767-300", "B767-400",
	"B772", "B773", "B77L", "B77W", "B777-200", "B777-300",
	"B788", "B789", "B78X", "B787-8", "B787-9", "B787-10",
	# McDonnell Douglas / Douglas
	"DC8", "DC-8", "DC9", "DC-9", "DC10", "DC-10",
	"MD10", "MD11",
	"MD80", "MD81", "MD82", "MD83", "MD87", "MD88", "MD90",
	# Embraer & regional jets
	"ERJ135", "ERJ140", "ERJ145",
	"E135", "E140", "E145",
	"E170", "E175", "E190", "E195",
	"E170-E2", "E190-E2", "E195-E2",
	"EMB-110", "EMB110", "EMB-120", "EMB120",
	# Bombardier / De Havilland Canada
	"CRJ1", "CRJ2", "CRJ-200", "CRJ7", "CRJ-700", "CRJ9", "CRJ-900",
	"CRJ10", "CRJ-1000", "CRJX",
	"DHC-6", "DHC-7", "DHC-8",
	"DH8A", "DH8B", "DH8C", "DH8D",
	"Q100", "Q200", "Q300", "Q400",
	# ATR
	"ATR 42", "ATR-42", "ATR42",
	"ATR 72", "ATR-72", "ATR72",
	"AT45", "AT46", "AT72", "AT75", "AT76",
	# Fokker
	"F27", "F28", "F50", "F70", "F100",
	# British Aerospace / Avro
	"BAE 146", "BAE-146", "RJ70", "RJ85", "RJ100",
	"Avro RJ85", "Avro RJ100",
	# Saab / Fairchild Dornier
	"SF34", "SAAB 340", "SAAB 2000",
	"Do 228", "Do 328", "Dornier 228", "Dornier 328", "328JET",
	# Shorts
	"SH33", "SH36", "Short 330", "Short 360",
	# Beechcraft / Cessna / Piper / Pilatus / misc GA
	"BE20", "BE30", "BE35", "BE36", "BE99", "B190", "B200",
	"C152", "C172", "C182", "C185", "C188",
	"C206", "C208", "C210", "C310", "C340", "C402", "C404",
	"C414", "C421", "C425", "C441",
	"PA-23", "PA-28", "PA-31", "PA-34", "PA-42", "PA-46",
	"PC-6", "PC-7", "PC-9", "PC-12", "PC12",
	"SR20", "SR22",
	"DA40", "DA42", "DA62",
	"TBM700", "TBM-700", "TBM850", "TBM900",
	# Helicopters & tilt-rotor (common mentions)
	"AS350", "AS355", "EC120", "EC130", "EC135", "EC145",
	"EC155", "EC175", "EC225",
	"BK117", "BO105",
	"B212", "B412", "B429",
	"S61", "S76", "S92",
	"AW109", "AW139", "AW169", "AW189",
	"UH-60", "S-70",
	# Soviet / Russian / Chinese types
	"AN2", "AN12", "AN24", "AN26", "AN28", "AN30", "AN32",
	"AN72", "AN124", "AN140", "AN148",
	"IL18", "IL62", "IL76", "IL86", "IL96",
	"TU134", "TU154", "TU204",
	"Yak-40", "Yak-42",
	"Superjet 100", "SSJ100",
	"MA60", "MA600", "ARJ21", "C919",
	# Misc popular models
	"BN2", "BN-2", "Islander", "Trislander",
	"JS31", "JS32", "JS41",
	"L410", "Let 410",
	"Metro III", "Metro 23", "SW3", "SW4",
	"King Air", "Twin Otter", "Grand Caravan"
]

