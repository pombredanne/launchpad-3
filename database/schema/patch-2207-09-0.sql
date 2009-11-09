-- Copyright 2009 Canonical Ltd.  This software is licensed under the
-- GNU Affero General Public License version 3 (see the file LICENSE).

SET client_min_messages=ERROR;

-- The schema patch required for the Soyuz buildd generalisation, see
-- https://dev.launchpad.net/Soyuz/Specs/BuilddGeneralisation for details.

-- Step 1
-- The `BuildPackageJob` table captures whatever data is required for
-- "normal" Soyuz build farm jobs that build source packages.

CREATE TABLE buildpackagejob (
  id serial PRIMARY KEY,
  -- FK to the `Job` record with "generic" data about this source package
  -- build job. Please note that the corresponding `BuildQueue` row will
  -- have a FK referencing the same `Job` row.
  job integer NOT NULL CONSTRAINT buildpackagejob__job__fk REFERENCES job,
  -- FK to the associated `Build` record.
  build integer NOT NULL CONSTRAINT buildpackagebuild__build__fk
  REFERENCES build
);

-- Step 2
-- Changes needed to the `BuildQueue` table.

-- First remove the 'build' column and the associated index and constraint
-- from `BuildQueue`.
-- The latter will from now on refer to the `Build` record via the
-- `Job`/`BuildPackageJob` tables (and not directly any more).
DROP INDEX buildqueue__build__idx;
ALTER TABLE ONLY buildqueue DROP CONSTRAINT "$1";
ALTER TABLE ONLY buildqueue DROP COLUMN build;

-- The 'job' and the 'job_type' columns added to the `BuildQueue` table
-- will enable us to find the correct database rows that hold the generic
-- and the specific data pertaining to the job respectively.
ALTER TABLE ONLY buildqueue ADD COLUMN 
  job integer NOT NULL CONSTRAINT buildqueue__job__fk REFERENCES job;
CREATE INDEX buildqueue__job__idx ON buildqueue(job);

ALTER TABLE ONLY buildqueue ADD COLUMN job_type integer NOT NULL DEFAULT 1;
CREATE INDEX buildqueue__job_type__idx ON buildqueue(job_type);

INSERT INTO LaunchpadDatabaseRevision VALUES (2207, 09, 0);
