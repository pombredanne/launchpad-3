SET client_min_messages=ERROR;

ALTER TABLE StandardShipitRequest ADD COLUMN description text;

INSERT INTO LaunchpadDatabaseRevision VALUES (88, 02, 0);
