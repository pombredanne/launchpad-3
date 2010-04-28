SET client_min_messages=ERROR;

-- Indices for BugJob
CREATE UNIQUE INDEX bugjob__job__key ON BugJob(job);
CREATE INDEX bugjob__bug__job_type__idx ON BugJob(bug, job_type);

-- Indices for Job
CREATE INDEX job__scheduled_start__idx ON Job(scheduled_start);
CREATE INDEX job__lease_expires__idx ON Job(lease_expires);

INSERT INTO LaunchpadDatabaseRevision VALUES (2207, 53, 0);
