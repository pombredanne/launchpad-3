SET client_min_messages=ERROR;

ALTER TABLE Distribution ADD COLUMN official_malone boolean;
ALTER TABLE Distribution ADD COLUMN official_rosetta boolean;
ALTER TABLE Distribution ALTER COLUMN official_malone SET DEFAULT FALSE;
ALTER TABLE Distribution ALTER COLUMN official_rosetta SET DEFAULT FALSE;

/* Only Ubuntu and Baltix use Malone and Rosetta at the moment. */
UPDATE Distribution SET official_malone = FALSE;
UPDATE Distribution SET official_rosetta = FALSE;
UPDATE Distribution SET official_malone = TRUE WHERE NAME = 'ubuntu';
UPDATE Distribution SET official_rosetta = TRUE WHERE NAME = 'ubuntu';
UPDATE Distribution SET official_malone = TRUE WHERE NAME = 'baltix';
UPDATE Distribution SET official_rosetta = TRUE WHERE NAME = 'baltix';

ALTER TABLE Distribution ALTER COLUMN official_malone SET NOT NULL;
ALTER TABLE Distribution ALTER COLUMN official_rosetta SET NOT NULL;

INSERT INTO LaunchpadDatabaseRevision VALUES (40, 19, 0);

