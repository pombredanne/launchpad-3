
SET client_min_messages = ERROR;

ALTER TABLE POFile ADD COLUMN exportfile INTEGER REFERENCES LibraryFileAlias;
ALTER TABLE POFile ADD COLUMN exporttime TIMESTAMP WITHOUT TIME ZONE;

INSERT INTO LaunchpadDatabaseRevision VALUES (17, 10, 0);

