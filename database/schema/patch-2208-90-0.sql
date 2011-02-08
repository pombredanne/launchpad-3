SET client_min_messages=ERROR;

CREATE TABLE ProductSeriesPackageLinkJob (
    id SERIAL PRIMARY KEY,
    job INTEGER NOT NULL CONSTRAINT job_fk REFERENCES Job ON DELETE CASCADE,
    job_type INTEGER NOT NULL,
    productseries INTEGER NOT NULL CONSTRAINT productseries_fk REFERENCES ProductSeries,
    sourcepackagename INTEGER NOT NULL CONSTRAINT sourcepackagename_fk REFERENCES SourcePackageName,
    distroseries INTEGER NOT NULL CONSTRAINT distroseries_fk REFERENCES DistroSeries
);

INSERT INTO LaunchpadDatabaseRevision VALUES (2208, 90, 0);
