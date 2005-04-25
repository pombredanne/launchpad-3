SET client_min_messages=ERROR;

ALTER TABLE Packaging ADD CONSTRAINT packaging_pkey primary key(id);
UPDATE Packaging SET id=DEFAULT WHERE id IS NULL;

INSERT INTO LaunchpadDatabaseRevision VALUES (14, 09, 0);

