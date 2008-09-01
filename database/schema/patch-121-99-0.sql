SET client_min_messages=ERROR;

CREATE TABLE PackageBugReportingGuideline (
  id serial PRIMARY KEY,

  distribution integer REFERENCES Distribution,
  sourcepackagename integer REFERENCES SourcePackageName,

  bug_reporting_guidelines TEXT NOT NULL,

  UNIQUE (sourcepackagename, distribution)
);

INSERT INTO LaunchpadDatabaseRevision VALUES (121, 99, 0);
