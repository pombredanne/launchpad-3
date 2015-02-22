-- Copyright 2015 Canonical Ltd.  This software is licensed under the
-- GNU Affero General Public License version 3 (see the file LICENSE).

SET client_min_messages=ERROR;

CREATE INDEX buildqueue__status__lastscore__id__idx ON
    buildqueue (status, lastscore DESC, id);

INSERT INTO LaunchpadDatabaseRevision VALUES (2209, 62, 0);
