SET client_min_messages=ERROR;

ALTER TABLE Distribution ADD COLUMN security_contact INTEGER REFERENCES Person(id);
ALTER TABLE Product ADD COLUMN security_contact INTEGER REFERENCES Person(id);
ALTER TABLE Bug ADD COLUMN security_related BOOLEAN;
UPDATE Bug SET security_related = FALSE;
ALTER TABLE Bug ALTER COLUMN security_related SET DEFAULT FALSE;
ALTER TABLE Bug ALTER COLUMN security_related SET NOT NULL;

INSERT INTO LaunchpadDatabaseRevision VALUES (40, 46, 0);