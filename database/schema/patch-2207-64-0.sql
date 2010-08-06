-- Copyright 2009 Canonical Ltd.  This software is licensed under the
-- GNU Affero General Public License version 3 (see the file LICENSE).

SET client_min_messages=ERROR;

-- The schema patch required for adding archive jobs, the first being
-- creation of copy archives.

-- The `DistroSeriesJob` table captures the data required for an archive job.

CREATE TABLE DistroSeriesJob (
    id serial PRIMARY KEY,
    -- FK to the `Job` record with the "generic" data about this archive
    -- job.
    job integer NOT NULL CONSTRAINT distroseries__job__fk
        REFERENCES job ON DELETE CASCADE,
    -- FK to the associated `Archive` record.
    distroseries integer NOT NULL
        CONSTRAINT distroseriesjob__archive__fk REFERENCES DistroSeries,
    -- The particular type of archive job
    job_type integer NOT NULL,
    -- JSON data for use by the job
    json_data text
);

ALTER TABLE DistroSeriesJob ADD CONSTRAINT distroseries__job__key
    UNIQUE (job);
CREATE INDEX distroseriesjob__distroseries__job_type__idx
    ON DistroSeriesJob(distroseries, job_type);

INSERT INTO LaunchpadDatabaseRevision VALUES (2207, 64, 0);
