-- Copyright 2016 Canonical Ltd.  This software is licensed under the
-- GNU Affero General Public License version 3 (see the file LICENSE).

SET client_min_messages=ERROR;

CREATE INDEX libraryfilealias__expires__partial__idx
    ON libraryfilealias(expires)
    WHERE content IS NOT NULL AND expires IS NOT NULL;

INSERT INTO LaunchpadDatabaseRevision VALUES (2209, 77, 0);
