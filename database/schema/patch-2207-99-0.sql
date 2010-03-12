SET client_min_messages=ERROR;
ALTER TABLE sourcepackagerelease ADD changelog text;
INSERT INTO LaunchpadDatabaseRevision VALUES (2207, 99, 0);
