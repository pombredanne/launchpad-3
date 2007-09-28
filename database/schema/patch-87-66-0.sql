SET client_min_messages=ERROR;

ALTER TABLE standardshipitrequest ADD COLUMN description text;

INSERT INTO LaunchpadDatabaseRevision VALUES (87, 66, 0);
