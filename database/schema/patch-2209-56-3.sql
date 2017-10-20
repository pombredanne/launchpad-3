-- Copyright 2017 Canonical Ltd.  This software is licensed under the
-- GNU Affero General Public License version 3 (see the file LICENSE).

SET client_min_messages=ERROR;

ALTER TABLE LiveFS ADD COLUMN relative_build_score integer DEFAULT 0 NOT NULL;

COMMENT ON COLUMN LiveFS.relative_build_score IS 'A delta to the build score that is applied to all builds of this live filesystem.';

INSERT INTO LaunchpadDatabaseRevision VALUES (2209, 56, 3);
