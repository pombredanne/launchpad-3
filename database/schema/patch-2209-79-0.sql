-- Copyright 2016 Canonical Ltd.  This software is licensed under the
-- GNU Affero General Public License version 3 (see the file LICENSE).

SET client_min_messages=ERROR;

ALTER TABLE ArchiveAuthToken
    ALTER COLUMN person DROP NOT NULL,
    ADD COLUMN name text;

CREATE INDEX archiveauthtoken__name__idx ON ArchiveAuthToken USING btree (name);

INSERT INTO LaunchpadDatabaseRevision VALUES (2209, 79, 0);
