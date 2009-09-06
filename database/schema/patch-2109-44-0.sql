-- Copyright 2009 Canonical Ltd.  This software is licensed under the
-- GNU Affero General Public License version 3 (see the file LICENSE).

SET client_min_messages=ERROR;

UPDATE Revision SET revision_date=date_created
WHERE revision_date > date_created;

INSERT INTO LaunchpadDatabaseRevision VALUES (2109, 44, 0);
