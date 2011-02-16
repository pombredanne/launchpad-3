-- Copyright 2011 Canonical Ltd.  This software is licensed under the
-- GNU Affero General Public License version 3 (see the file LICENSE).
SET client_min_messages=ERROR;

ALTER TABLE BugNotification
    ADD COLUMN is_omitted BOOLEAN NOT NULL DEFAULT False;

INSERT INTO LaunchpadDatabaseRevision VALUES (2208, 99, 1);
