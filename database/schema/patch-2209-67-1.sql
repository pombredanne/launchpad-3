-- Copyright 2015 Canonical Ltd.  This software is licensed under the
-- GNU Affero General Public License version 3 (see the file LICENSE).

SET client_min_messages=ERROR;

ALTER TABLE product ADD COLUMN access_policies integer[];

CREATE INDEX accesspolicygrantflat__grantee__policy__idx
    ON accesspolicygrantflat (grantee, policy);

INSERT INTO LaunchpadDatabaseRevision VALUES (2209, 67, 1);
