-- Copyright 2009 Canonical Ltd.  This software is licensed under the
-- GNU Affero General Public License version 3 (see the file LICENSE).

SET client_min_messages=ERROR;

-- The `InitialiseDistroSeriesJob` table captures the data required for an ifp job.

CREATE TABLE InitialiseDistroSeriesJob (
    id serial PRIMARY KEY,
    -- FK to the `Job` record with the "generic" data about this archive
    -- job.
    job integer NOT NULL CONSTRAINT initialisedistroseriesjob__job__fk REFERENCES job,
    -- FK to the associated `InitialiseDistroSeries` record.
    distroseries integer NOT NULL CONSTRAINT initialisedistroseriesjob__distroseries__fk REFERENCES DistroSeries,
    -- JSON data for use by the job
    json_data text
);

ALTER TABLE InitialiseDistroSeriesJob ADD CONSTRAINT initialisedistroseriesjob__job__key UNIQUE (job);

INSERT INTO LaunchpadDatabaseRevision VALUES (2207, 99, 0);

