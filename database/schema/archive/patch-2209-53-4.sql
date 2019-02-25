-- Copyright 2014 Canonical Ltd.  This software is licensed under the
-- GNU Affero General Public License version 3 (see the file LICENSE).

SET client_min_messages=ERROR;

DROP VIEW IF EXISTS exclusivelocks;
DROP VIEW IF EXISTS alllocks;

INSERT INTO LaunchpadDatabaseRevision VALUES (2209, 53, 4);
