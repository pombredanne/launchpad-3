-- Copyright 2013 Canonical Ltd.  This software is licensed under the
-- GNU Affero General Public License version 3 (see the file LICENSE).

SET client_min_messages=ERROR;

ALTER TABLE buildqueue
    ADD COLUMN build_farm_job integer REFERENCES buildfarmjob,
    ADD COLUMN status integer,
    ADD COLUMN date_started timestamp without time zone;

ALTER TABLE buildqueue ALTER COLUMN job DROP NOT NULL;
ALTER TABLE buildqueue ALTER COLUMN job_type DROP NOT NULL;

INSERT INTO LaunchpadDatabaseRevision VALUES (2209, 51, 0);
