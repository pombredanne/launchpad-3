-- Copyright 2013 Canonical Ltd.  This software is licensed under the
-- GNU Affero General Public License version 3 (see the file LICENSE).

SET client_min_messages=ERROR;

ALTER TABLE buildqueue DROP CONSTRAINT buildqueue__job__fk;
ALTER TABLE buildpackagejob DROP CONSTRAINT buildpackagejob__job__fk;
ALTER TABLE sourcepackagerecipebuildjob
    DROP CONSTRAINT sourcepackagerecipebuildjob_job_fkey;

INSERT INTO LaunchpadDatabaseRevision VALUES (2209, 51, 1);
