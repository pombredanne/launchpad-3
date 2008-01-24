SET client_min_messages=ERROR;

UPDATE Person SET
    verbose_bugnotifications = COALESCE(verbose_bugnotifications, FALSE),
    visibility = COALESCE(visibility, 1)
WHERE verbose_bugnotifications IS NULL OR visibility IS NULL;

ALTER TABLE Person
    ALTER COLUMN verbose_bugnotifications SET NOT NULL,
    ALTER COLUMN verbose_bugnotifications SET DEFAULT FALSE,
    ALTER COLUMN visibility SET NOT NULL,
    ALTER COLUMN visibility SET DEFAULT 1;

INSERT INTO LaunchpadDatabaseRevision VALUES (88, 51, 0);

