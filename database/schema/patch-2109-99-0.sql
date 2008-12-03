SET client_min_messages=ERROR;

ALTER TABLE Translator ADD COLUMN documentation_url text;


INSERT INTO LaunchpadDatabaseRevision VALUES (2109, 99, 0);

