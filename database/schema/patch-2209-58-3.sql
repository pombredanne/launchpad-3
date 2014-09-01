-- Copyright 2014 Canonical Ltd.  This software is licensed under the
-- GNU Affero General Public License version 3 (see the file LICENSE).

SET client_min_messages=ERROR;

-- STEP 6, LIVE.
-- LibraryFileAlias indexes, to be done concurrently.
CREATE INDEX libraryfilealias__content__idx ON LibraryFileAlias(_content);

INSERT INTO LaunchpadDatabaseRevision VALUES (2209, 58, 3);
