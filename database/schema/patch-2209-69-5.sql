-- Copyright 2016 Canonical Ltd.  This software is licensed under the
-- GNU Affero General Public License version 3 (see the file LICENSE).

SET client_min_messages=ERROR;

ALTER TABLE Snap ADD COLUMN store_channels text;

COMMENT ON COLUMN Snap.store_channels IS 'Channels to which to release this snap package after uploading it to the store.';

INSERT INTO LaunchpadDatabaseRevision VALUES (2209, 69, 5);
