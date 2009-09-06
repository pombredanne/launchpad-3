-- Copyright 2009 Canonical Ltd.  This software is licensed under the
-- GNU Affero General Public License version 3 (see the file LICENSE).

SET client_min_messages=ERROR;
ALTER TABLE Product ADD COLUMN remote_product text; 
INSERT INTO LaunchpadDatabaseRevision VALUES (2109, 18, 0);
