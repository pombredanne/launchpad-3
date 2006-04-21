SET client_min_messages=ERROR;

ALTER TABLE LoginToken ADD COLUMN date_consumed timestamp without time zone;

INSERT INTO LaunchpadDatabaseRevision VALUES (40, 47, 0);

