-- Copyright 2013 Canonical Ltd.  This software is licensed under the
-- GNU Affero General Public License version 3 (see the file LICENSE).

SET client_min_messages=ERROR;

ALTER TABLE buildqueue
    DROP COLUMN job,
    DROP COLUMN job_type,
    ALTER COLUMN virtualized SET NOT NULL,
    ALTER COLUMN build_farm_job SET NOT NULL,
    ALTER COLUMN status SET NOT NULL;
DROP TABLE buildpackagejob;
DROP TABLE sourcepackagerecipebuildjob;

INSERT INTO LaunchpadDatabaseRevision VALUES (2209, 51, 2);
