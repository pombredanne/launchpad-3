-- Copyright 2018 Canonical Ltd.  This software is licensed under the
-- GNU Affero General Public License version 3 (see the file LICENSE).

SET client_min_messages=ERROR;

ALTER TABLE SnapBuild ADD COLUMN build_request integer REFERENCES job;

COMMENT ON COLUMN SnapBuild.build_request IS 'The build request that caused this build to be created.';

INSERT INTO LaunchpadDatabaseRevision VALUES (2209, 83, 4);
