SET client_min_messages=ERROR;

ALTER TABLE Announcement ALTER COLUMN date_announced SET DEFAULT NULL;
ALTER TABLE Announcement ADD COLUMN date_updated timestamp without time zone
    DEFAULT NULL;

INSERT INTO LaunchpadDatabaseRevision VALUES (88, 22, 1);
