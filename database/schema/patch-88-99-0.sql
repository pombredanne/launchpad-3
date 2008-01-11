SET client_min_messages=ERROR;

UPDATE POTemplate SET header='' WHERE header IS NULL;

ALTER TABLE POTemplate ALTER header SET NOT NULL;

INSERT INTO LaunchpadDatabaseRevision VALUES (88, 99, 0);

