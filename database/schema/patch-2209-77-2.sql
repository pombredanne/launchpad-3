-- Copyright 2016 Canonical Ltd.  This software is licensed under the
-- GNU Affero General Public License version 3 (see the file LICENSE).

SET client_min_messages=ERROR;

CREATE UNIQUE INDEX packagediff__from_source__to_source__key
    ON packagediff(from_source, to_source);

INSERT INTO LaunchpadDatabaseRevision VALUES (2209, 77, 2);
