-- Copyright 2013 Canonical Ltd.  This software is licensed under the
-- GNU Affero General Public License version 3 (see the file LICENSE).

SET client_min_messages=ERROR;

ALTER TABLE buildqueue
    ADD COLUMN build_farm_job integer
        CONSTRAINT buildqueue__build_farm_job__fk REFERENCES buildfarmjob,
    ADD COLUMN status integer,
    ADD COLUMN date_started timestamp without time zone,
    ALTER COLUMN job DROP NOT NULL,
    ALTER COLUMN job_type DROP NOT NULL;
CREATE UNIQUE INDEX buildqueue__build_farm_job__key
    ON buildqueue (build_farm_job);

INSERT INTO LaunchpadDatabaseRevision VALUES (2209, 51, 0);
