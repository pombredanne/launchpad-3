SET client_min_messages=ERROR;

ALTER TABLE Distribution ADD COLUMN mirror_admin integer REFERENCES Person(id);

UPDATE Distribution SET mirror_admin = owner;

ALTER TABLE Distribution ALTER COLUMN mirror_admin SET NOT NULL;

INSERT INTO LaunchpadDatabaseRevision VALUES (40, 63, 0);

