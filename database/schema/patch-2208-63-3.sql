-- Copyright 2011 Canonical Ltd.  This software is licensed under the
-- GNU Affero General Public License version 3 (see the file LICENSE).

SET client_min_messages=ERROR;


-- Create a journal for BugSummary updates.
-- This is a separate DB patch as the table needs to be created and
-- added to replication before triggers are created, and we want to
-- do this live. We discussed not replicating this table, but this
-- would break our ability to failover to a new master.

CREATE TABLE BugSummaryJournal (
    id serial PRIMARY KEY,
    count INTEGER NOT NULL default 0,
    product INTEGER REFERENCES Product ON DELETE CASCADE,
    productseries INTEGER REFERENCES ProductSeries ON DELETE CASCADE,
    distribution INTEGER REFERENCES Distribution ON DELETE CASCADE,
    distroseries INTEGER REFERENCES DistroSeries ON DELETE CASCADE,
    sourcepackagename INTEGER REFERENCES SourcePackageName ON DELETE CASCADE,
    viewed_by INTEGER REFERENCES Person ON DELETE CASCADE,
    tag TEXT,
    status INTEGER NOT NULL,
    milestone INTEGER REFERENCES Milestone ON DELETE CASCADE);

-- Fat index for fast lookups
CREATE INDEX bugsummaryjournal__full__idx ON BugSummaryJournal (
    status, product, productseries, distribution, distroseries,
    sourcepackagename, viewed_by, milestone, tag);

-- Indexes for fast deletions.
CREATE INDEX bugsummaryjournal__viewed_by__idx
    ON BugSummaryJournal(viewed_by) WHERE viewed_by IS NOT NULL;
CREATE INDEX bugsummaryjournal__milestone__idx
    ON BugSummaryJournal(milestone) WHERE milestone IS NOT NULL;


-- Combined view so we don't have to manually collate rows from both tables.
-- Note that we lose the id column - that only exists to keep replication
-- happy.
CREATE OR REPLACE VIEW CombinedBugSummary AS (
    SELECT
        count, product, productseries, distribution, distroseries,
        sourcepackagename, viewed_by, tag, status, milestone
    FROM BugSummaryJournal
    UNION ALL
    SELECT
        count, product, productseries, distribution, distroseries,
        sourcepackagename, viewed_by, tag, status, milestone
    FROM BugSummary);

INSERT INTO LaunchpadDatabaseRevision VALUES (2208, 63, 3);
