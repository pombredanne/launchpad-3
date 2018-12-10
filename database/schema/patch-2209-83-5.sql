-- Copyright 2018 Canonical Ltd.  This software is licensed under the
-- GNU Affero General Public License version 3 (see the file LICENSE).

SET client_min_messages=ERROR;

ALTER TABLE SnapBuild ADD COLUMN store_upload_json_data text;

COMMENT ON COLUMN SnapBuild.store_upload_json_data IS 'Data that is specific to a particular build.';

INSERT INTO LaunchpadDatabaseRevision VALUES (2209, 83, 5);
