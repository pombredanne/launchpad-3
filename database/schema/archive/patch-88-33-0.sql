SET client_min_messages=ERROR;

ALTER TABLE Product
      ADD COLUMN bug_reporting_guidelines TEXT;

ALTER TABLE Project
      ADD COLUMN bug_reporting_guidelines TEXT;

ALTER TABLE Distribution
      ADD COLUMN bug_reporting_guidelines TEXT;

INSERT INTO LaunchpadDatabaseRevision
       VALUES (88, 33, 0);
