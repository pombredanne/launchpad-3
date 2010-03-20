SET client_min_messages=ERROR;
ALTER TABLE sourcepackagerelease ADD changelog int REFERENCES libraryfilealias(id);
INSERT INTO LaunchpadDatabaseRevision VALUES (2207, 99, 0);
