set client_min_messages=ERROR;

ALTER TABLE Builder ADD COLUMN manual boolean;
ALTER TABLE Builder ALTER COLUMN manual SET DEFAULT false;

INSERT INTO LaunchpadDatabaseRevision VALUES (25,40,0);
