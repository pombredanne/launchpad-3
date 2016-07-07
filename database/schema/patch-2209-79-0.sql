-- Copyright 2016 Canonical Ltd.  This software is licensed under the
-- GNU Affero General Public License version 3 (see the file LICENSE).

SET client_min_messages=ERROR;

ALTER TABLE ArchiveAuthToken
    ALTER COLUMN person DROP NOT NULL,
    ADD COLUMN name text;

COMMENT ON COLUMN ArchiveAuthToken.name IS 'The name for this named token.';

CREATE INDEX archiveauthtoken__archive__name__date_deactivated__idx ON ArchiveAuthToken(archive, name) WHERE date_deactivated IS NULL;

INSERT INTO LaunchpadDatabaseRevision VALUES (2209, 79, 0);
