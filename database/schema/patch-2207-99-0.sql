SET client_min_messages=ERROR;

-- Indices for BugJob
CREATE INDEX bugjob__job ON BugJob(job);
CREATE INDEX bugjob__bug ON BugJob(bug);
CREATE INDEX bugjob__job_type ON BugJob(job_type);

-- Indices for Job
CREATE INDEX job__scheduled_start ON Job(scheduled_start);
CREATE INDEX job__lease_expires ON Job(lease_expires);

INSERT INTO LaunchpadDatabaseRevision VALUES (2207, 99, 0);
