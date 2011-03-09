-- Copyright 2009 Canonical Ltd.  This software is licensed under the
-- GNU Affero General Public License version 3 (see the file LICENSE).

SET client_min_messages=ERROR;

-- add a registrant column to distributions
ALTER TABLE Distribution
    ADD COLUMN registrant integer REFERENCES Person;

INSERT INTO LaunchpadDatabaseRevision VALUES (2208, 99, 0);
