SET client_min_messages=ERROR;

ALTER TABLE ticket ADD COLUMN language integer REFERENCES Language(id);

UPDATE ticket SET language = 119;

ALTER TABLE ticket ALTER COLUMN language SET NOT NULL;

INSERT INTO LaunchpadDatabaseRevision VALUES (67, 29, 0);
