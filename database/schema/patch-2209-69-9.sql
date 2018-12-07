-- Copyright 2018 Canonical Ltd.  This software is licensed under the
-- GNU Affero General Public License version 3 (see the file LICENSE).

SET client_min_messages=ERROR;

CREATE INDEX snapfile__libraryfile__idx ON snapfile(libraryfile);

INSERT INTO LaunchpadDatabaseRevision VALUES (2209, 69, 9);
