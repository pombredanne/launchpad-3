-- Copyright 2017 Canonical Ltd.  This software is licensed under the
-- GNU Affero General Public License version 3 (see the file LICENSE).

SET client_min_messages=ERROR;

ALTER TABLE SnapBuild ADD COLUMN revision_id text;

COMMENT ON COLUMN SnapBuild.revision_id IS 'The revision ID of the branch used for this build, if available.';

INSERT INTO LaunchpadDatabaseRevision VALUES (2209, 69, 8);
