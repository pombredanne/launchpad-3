
SET client_min_messages=ERROR;

/* Keep track of who provided us with the latest packaging info for a
 * package. */

ALTER TABLE Packaging ADD COLUMN datecreated timestamp without time zone;
ALTER TABLE Packaging ALTER COLUMN datecreated
    SET DEFAULT CURRENT_TIMESTAMP AT TIME ZONE 'UTC';
UPDATE Packaging SET datecreated=DEFAULT WHERE datecreated IS NULL;
ALTER TABLE Packaging ALTER COLUMN datecreated SET NOT NULL;

ALTER TABLE Packaging ADD COLUMN owner integer;
ALTER TABLE Packaging ADD CONSTRAINT packaging_owner_fk FOREIGN KEY (owner)
    REFERENCES Person(id);

INSERT INTO LaunchpadDatabaseRevision VALUES (17, 37, 0);

