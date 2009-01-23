SET client_min_messages=ERROR;

CREATE TABLE DistributionSourcePackage (
    id serial PRIMARY KEY,

    distribution integer NOT NULL
        CONSTRAINT distributionpackage__distribution__fk
        REFERENCES Distribution,
    sourcepackagename integer NOT NULL
        CONSTRAINT distributionpackage__sourcepackagename__fk
        REFERENCES SourcePackageName,

    bug_reporting_guidelines TEXT,

    CONSTRAINT distributionpackage__sourcepackagename__distribution__key
        UNIQUE (sourcepackagename, distribution)
);

INSERT INTO LaunchpadDatabaseRevision VALUES (121, 84, 0);
