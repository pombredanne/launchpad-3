-- Copyright 2009 Canonical Ltd.  This software is licensed under the
-- GNU Affero General Public License version 3 (see the file LICENSE).

SET client_min_messages=ERROR;

ALTER TABLE BugTracker
ADD COLUMN active BOOLEAN NOT NULL DEFAULT true;

INSERT INTO LaunchpadDatabaseRevision VALUES (2109, 23, 0);
