SET client_min_messages=ERROR;

CREATE TABLE PersonSettings (
    person integer PRIMARY KEY REFERENCES Person ON DELETE CASCADE,
    verbose_bugnotifications boolean NOT NULL DEFAULT FALSE,
    selfgenerated_bugnotifications boolean NOT NULL DEFAULT TRUE);

INSERT INTO PersonSettings (person, verbose_bugnotifications)
SELECT id, verbose_bugnotifications FROM Person;

ALTER TABLE Person DROP COLUMN verbose_bugnotifications;

INSERT INTO LaunchpadDatabaseRevision VALUES (2208, 38, 0);
