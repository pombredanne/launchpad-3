SET client_min_messages=ERROR;

ALTER TABLE Person ADD COLUMN renewal_policy integer;
UPDATE Person SET renewal_policy = 10;
ALTER TABLE Person ALTER COLUMN renewal_policy SET NOT NULL;

INSERT INTO LaunchpadDatabaseRevision VALUES (87, 03, 0);
