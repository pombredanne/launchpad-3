-- Copyright 2016 Canonical Ltd.  This software is licensed under the
-- GNU Affero General Public License version 3 (see the file LICENSE).

SET client_min_messages=ERROR;

ALTER TABLE PersonSettings ALTER COLUMN expanded_notification_footers SET NOT NULL;

INSERT INTO LaunchpadDatabaseRevision VALUES (2209, 68, 1);
