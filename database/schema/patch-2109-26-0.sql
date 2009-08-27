-- Copyright 2009 Canonical Ltd.  This software is licensed under the
-- GNU Affero General Public License version 3 (see the file LICENSE).

SET client_min_messages=ERROR;

UPDATE Branch
SET lifecycle_status=30 -- DEVELOPMENT
WHERE lifecycle_status=1; -- NEW

INSERT INTO LaunchpadDatabaseRevision VALUES (2109, 26, 0);
