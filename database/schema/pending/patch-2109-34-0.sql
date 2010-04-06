-- Copyright 2009 Canonical Ltd.  This software is licensed under the
-- GNU Affero General Public License version 3 (see the file LICENSE).

SET client_min_messages=ERROR;

ALTER TABLE Person
    DROP COLUMN addressline1,
    DROP COLUMN addressline2,
    DROP COLUMN organization,
    DROP COLUMN city,
    DROP COLUMN province,
    DROP COLUMN country,
    DROP COLUMN postcode,
    DROP COLUMN phone;


INSERT INTO LaunchpadDatabaseRevision VALUES (2109, 34, 0);
