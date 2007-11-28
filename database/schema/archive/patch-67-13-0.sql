SET client_min_messages = ERROR;

ALTER TABLE sourcepackagerelease ALTER column architecturehintlist SET NOT NULL;

INSERT INTO LaunchpadDatabaseRevision VALUES (67, 13, 0);
