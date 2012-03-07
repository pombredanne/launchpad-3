-- Copyright 2012 Canonical Ltd.  This software is licensed under the
-- GNU Affero General Public License version 3 (see the file LICENSE).

SET client_min_messages=ERROR;

-- Prepare to remove the old access policy schema.
ALTER TABLE Branch ADD COLUMN information_type INTEGER DEFAULT 1;
ALTER TABLE Bug ADD COLUMN information_type INTEGER DEFAULT 1;

INSERT INTO LaunchpadDatabaseRevision VALUES (2209, 12, 0);
