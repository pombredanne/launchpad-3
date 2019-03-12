-- Copyright 2018 Canonical Ltd.  This software is licensed under the
-- GNU Affero General Public License version 3 (see the file LICENSE).

SET client_min_messages=ERROR;

ALTER TABLE Snap ADD COLUMN auto_build_channels text;
ALTER TABLE SnapBuild ADD COLUMN channels text;

COMMENT ON COLUMN Snap.auto_build_channels IS 'A dictionary mapping snap names to channels to use when building this snap package.';
COMMENT ON COLUMN SnapBuild.channels IS 'A dictionary mapping snap names to channels to use for this build.';

INSERT INTO LaunchpadDatabaseRevision VALUES (2209, 83, 1);
