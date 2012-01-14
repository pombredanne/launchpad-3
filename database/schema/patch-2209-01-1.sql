-- Copyright 2012 Canonical Ltd.  This software is licensed under the
-- GNU Affero General Public License version 3 (see the file LICENSE).
SET client_min_messages=ERROR;

ALTER TABLE emailaddress DROP COLUMN account;
ALTER TABLE emailaddress ALTER COLUMN person SET NOT NULL;

INSERT INTO LaunchpadDatabaseRevision VALUES (2209, 01, 1);
