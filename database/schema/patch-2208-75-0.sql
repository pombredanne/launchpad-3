-- Copyright 2011 Canonical Ltd.  This software is licensed under the
-- GNU Affero General Public License version 3 (see the file LICENSE).

SET client_min_messages=ERROR;

-- Cleanup of BugSummary deferred until next downtime window.

ALTER TABLE BugSummary ADD CONSTRAINT bugsummary__viewed_by__fk
    FOREIGN KEY (viewed_by) REFERENCES Person;

INSERT INTO LaunchpadDatabaseRevision VALUES (2208, 75, 0);
