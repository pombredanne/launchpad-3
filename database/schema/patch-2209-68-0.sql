-- Copyright 2015 Canonical Ltd.  This software is licensed under the
-- GNU Affero General Public License version 3 (see the file LICENSE).

SET client_min_messages=ERROR;

ALTER TABLE PersonSettings ADD COLUMN expanded_notification_footers boolean;

COMMENT ON COLUMN PersonSettings.expanded_notification_footers IS 'Include filtering information in e-mail footers.';

INSERT INTO LaunchpadDatabaseRevision VALUES (2209, 68, 0);
