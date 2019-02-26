-- Copyright 2015 Canonical Ltd.  This software is licensed under the
-- GNU Affero General Public License version 3 (see the file LICENSE).

SET client_min_messages=ERROR;

ALTER TABLE LiveFSBuild ADD COLUMN version text;

COMMENT ON COLUMN LiveFSBuild.version IS 'A version string for this build.';

INSERT INTO LaunchpadDatabaseRevision VALUES (2209, 56, 2);
