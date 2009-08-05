-- Copyright 2009 Canonical Ltd.  This software is licensed under the
-- GNU Affero General Public License version 3 (see the file LICENSE).

SET client_min_messages = ERROR;

ALTER TABLE BugTask
ADD COLUMN date_left_closed TIMESTAMP WITHOUT TIME ZONE;

INSERT INTO LaunchpadDatabaseRevision VALUES (2109, 10, 0);
