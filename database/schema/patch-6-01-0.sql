SET client_min_messages = ERROR;

/* Karma table for salgardo */

CREATE TABLE Karma (
    id SERIAL PRIMARY KEY,
    karmafield INT NOT NULL,
    datecreated TIMESTAMP NOT NULL,
    person INT NOT NULL,
    CONSTRAINT karma_person_fk FOREIGN KEY (person) REFERENCES Person (id),
    points INT NOT NULL);

/* POTemplate fix for Carlos */
ALTER TABLE POTemplate DROP CONSTRAINT potemplate_rawimportstatus_valid;
ALTER TABLE POTemplate ADD CONSTRAINT potemplate_rawimportstatus_valid CHECK(((rawfile IS NULL) AND (rawimportstatus <> 1)) OR (rawfile IS NOT NULL));
ALTER TABLE POTemplate ALTER rawimportstatus SET DEFAULT 0;

ALTER TABLE POFile DROP CONSTRAINT potemplate_rawimportstatus_valid;
ALTER TABLE POFile ADD CONSTRAINT pofile_rawimportstatus_valid CHECK(((rawfile IS NULL) AND (rawimportstatus <> 1)) OR (rawfile IS NOT NULL));
ALTER TABLE POFile ALTER rawimportstatus SET DEFAULT 0;

UPDATE LaunchpadDatabaseRevision SET major=6, minor=1, patch=0;
