SET client_min_messages=ERROR;

ALTER TABLE Milestone ADD COLUMN description text;

INSERT INTO LaunchpadDatabaseRevision VALUES (87, 98, 8);
