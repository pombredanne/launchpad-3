-- Copyright 2009 Canonical Ltd.  This software is licensed under the
-- GNU Affero General Public License version 3 (see the file LICENSE).

SET client_min_messages=ERROR;

-- Adding a 'status' column for better handling failed request.
-- Set the default value so the NOT NULL constraint can be added.
-- A proper data migration will be done when the new code gets released.
ALTER TABLE PackageDiff ADD COLUMN status INTEGER DEFAULT 0 NOT NULL;

CREATE INDEX packagediff__status__idx ON PackageDiff(status);

DROP INDEX archivedependency__unique__temp;
ALTER TABLE ArchiveDependency
    DROP CONSTRAINT archivedependency_unique,
    ADD CONSTRAINT archivedependency__unique UNIQUE (archive, dependency),
    ALTER COLUMN pocket SET NOT NULL;

INSERT INTO LaunchpadDatabaseRevision VALUES (2109, 6, 0);
