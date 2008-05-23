SET client_min_messages=ERROR;

ALTER TABLE Branch
ADD COLUMN stacked_on integer REFERENCES Branch (id);

CREATE INDEX branch__stacked_on__idx ON Branch(stacked_on)
WHERE stacked_on IS NOT NULL;

INSERT INTO LaunchpadDatabaseRevision VALUES (121, 54, 0);
