-- Copyright 2010 Canonical Ltd.  This software is licensed under the
-- GNU Affero General Public License version 3 (see the file LICENSE).

SET client_min_messages=ERROR;

ALTER TABLE BugTrackerComponentGroup
    ADD COLUMN remote_name TEXT NOT NULL;

ALTER TABLE BugTrackerComponent
    ADD COLUMN remote_name TEXT NOT NULL;

INSERT INTO LaunchpadDatabaseRevision VALUES(2208, 99, 0);
