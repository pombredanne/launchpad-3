-- Copyright 2012 Canonical Ltd.  This software is licensed under the
-- GNU Affero General Public License version 3 (see the file LICENSE).

SET client_min_messages=ERROR;

ALTER TABLE packageupload ADD COLUMN searchable_names TEXT;
CREATE INDEX packageupload__searchable_names__trgm ON packageupload
    USING gin (searchable_names trgm.gin_trgm_ops);

INSERT INTO LaunchpadDatabaseRevision VALUES (2209, 40, 0);
