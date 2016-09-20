-- Copyright 2014 Canonical Ltd.  This software is licensed under the
-- GNU Affero General Public License version 3 (see the file LICENSE).

SET client_min_messages=ERROR;

-- STEP 3, LIVE
-- To be done CONCURRENTLY, create the UNIQUE index on LFC._id.
CREATE UNIQUE INDEX libraryfilecontent_id_key ON LibraryFileContent(_id);

INSERT INTO LaunchpadDatabaseRevision VALUES (2209, 58, 1);
