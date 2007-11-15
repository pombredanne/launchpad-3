SET client_min_messages=ERROR;

ALTER TABLE Announcement ALTER COLUMN date_announced SET DEFAULT NULL;

INSERT INTO LaunchpadDatabaseRevision VALUES (88, 22, 1);
