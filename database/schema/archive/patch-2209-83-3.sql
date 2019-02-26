-- Copyright 2018 Canonical Ltd.  This software is licensed under the
-- GNU Affero General Public License version 3 (see the file LICENSE).

SET client_min_messages=ERROR;

CREATE TABLE SnapJob (
    job integer PRIMARY KEY REFERENCES Job ON DELETE CASCADE NOT NULL,
    snap integer REFERENCES Snap NOT NULL,
    job_type integer NOT NULL,
    json_data text NOT NULL
);

CREATE INDEX snapjob__snap__job_type__job__idx
    ON SnapJob(snap, job_type, job);

COMMENT ON TABLE SnapJob IS 'Contains references to jobs that are executed for a snap package.';
COMMENT ON COLUMN SnapJob.job IS 'A reference to a Job row that has all the common job details.';
COMMENT ON COLUMN SnapJob.snap IS 'The snap package that this job is for.';
COMMENT ON COLUMN SnapJob.job_type IS 'The type of a job, such as a build request.';
COMMENT ON COLUMN SnapJob.json_data IS 'Data that is specific to a particular job type.';

INSERT INTO LaunchpadDatabaseRevision VALUES (2209, 83, 3);
