-- Copyright 2012 Canonical Ltd.  This software is licensed under the
-- GNU Affero General Public License version 3 (see the file LICENSE).

SET client_min_messages=ERROR;

-- All existing and future specifications are public, until model code supports overriding this.
ALTER TABLE Specification ADD COLUMN information_type INTEGER NOT NULL DEFAULT 1;

INSERT INTO LaunchpadDatabaseRevision VALUES (2209, 99, 0);
