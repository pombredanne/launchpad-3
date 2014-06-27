-- Copyright 2014 Canonical Ltd.  This software is licensed under the
-- GNU Affero General Public License version 3 (see the file LICENSE).

SET client_min_messages=ERROR;

CREATE INDEX buildqueue__status__virtualized__processor__lastscore__id__idx
    ON buildqueue(status, virtualized, processor, lastscore DESC, id);

INSERT INTO LaunchpadDatabaseRevision VALUES (2209, 53, 6);
