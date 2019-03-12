-- Copyright 2013 Canonical Ltd.  This software is licensed under the
-- GNU Affero General Public License version 3 (see the file LICENSE).

SET client_min_messages=ERROR;

ALTER TABLE builder ADD COLUMN version TEXT;

INSERT INTO LaunchpadDatabaseRevision VALUES (2209, 50, 0);
