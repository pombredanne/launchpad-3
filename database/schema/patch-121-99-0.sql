SET client_min_messages=ERROR;

-- Derived archives are generalized copy archives with a parent. We envision
-- they will be used for point releases, rebuilds, stable snapshots etc.

-- The concept of rebuild archives is being extended to generalized copy
-- archives.

-- Table 'archiverebuild' will hence be dropped and recreated as table
-- 'derivedarchive'.

-- Step 1: get rid of the old table ('archiverebuild')
DROP TABLE archiverebuild CASCADE;

-- Step 2: recreate the table as 'derivedarchive'.
CREATE TABLE derivedarchive (
    id serial PRIMARY KEY,
    -- The parent archive.
    archive integer NOT NULL,
    -- The associated DistroSeries.
    distroseries integer NOT NULL,
    -- The person who created the derived archive.
    registrant integer NOT NULL,
    -- The rebuild status if applicable (one of: new, in-progress, cancelled,
    -- succeeded, failed).
    rebuild_status integer NOT NULL,
    -- The reason why this derived archive was created (one-liner).
    reason text,
    -- When was this derived archive created?
    date_created timestamp without time zone
    DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'UTC') NOT NULL
);

-- Step 3: define the appropriate constraints.
ALTER TABLE ONLY derivedarchive
    ADD CONSTRAINT derivedarchive__archive__key UNIQUE (archive);

ALTER TABLE ONLY derivedarchive
    ADD CONSTRAINT derivedarchive__archive__fk
    FOREIGN KEY (archive) REFERENCES archive(id);

ALTER TABLE ONLY derivedarchive
    ADD CONSTRAINT derivedarchive__distroseries__fk
    FOREIGN KEY (distroseries) REFERENCES distroseries(id);

ALTER TABLE ONLY derivedarchive
    ADD CONSTRAINT derivedarchive__requestor__fk
    FOREIGN KEY (registrant) REFERENCES person(id);

-- Create new ArchiveCopyJob table.

-- Once a derived archive has been put into place the user will want to copy
-- packages to it (from the parent archive or any other archive of choice).
-- Some workflows may well result in multiple copy operations.

-- These inter-archive package copy operations may take quite a bit of time
-- and should hence not be tied to a web GUI request because the latter is
-- likely to time out.

-- Instead the user is to *specify* what packages should be copied and then
-- some background package copy service will pick up the archive copy job
-- specification and perform the actual copying of packages.

CREATE TABLE archivecopyjob (
    id serial PRIMARY KEY,

    -- This is the source archive from which packages are to be copied.
    source_archive integer NOT NULL,
    -- Copy packages belonging to this component.
    source_component integer NOT NULL,
    -- Copy packages belonging to this pocket.
    source_pocket integer NOT NULL,

    -- This is the target archive to which packages are to be copied.
    target_archive integer NOT NULL,
    -- This is the target component.
    target_component integer NOT NULL,
    -- This is the target pocket.
    target_pocket integer NOT NULL,

    -- Whether binary packages should be copied as well.
    copy_binaries boolean DEFAULT FALSE NOT NULL,

    -- The person who requested the inter-archive package copy operation.
    registrant integer NOT NULL,
    -- The copy job's status (new, in-progress, cancelled, succeeded, failed).
    status integer NOT NULL,
    -- The reason why this copy job was requested (one-liner).
    reason text,

    -- When was this copy job requested?
    date_created timestamp without time zone
    DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'UTC') NOT NULL,
    -- When was this copy job started?
    date_started timestamp without time zone
    DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'UTC') NOT NULL,
    -- When did this copy job conclude?
    date_completed timestamp without time zone
    DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'UTC') NOT NULL
);

ALTER TABLE ONLY archivecopyjob
    ADD CONSTRAINT archivecopyjob__sourcearchive__fk
    FOREIGN KEY (source_archive) REFERENCES archive(id);

ALTER TABLE ONLY archivecopyjob
    ADD CONSTRAINT archivecopyjob_sourcecomponent_fk
    FOREIGN KEY (source_component) REFERENCES component(id);

ALTER TABLE ONLY archivecopyjob
    ADD CONSTRAINT archivecopyjob__targetarchive__fk
    FOREIGN KEY (target_archive) REFERENCES archive(id);

ALTER TABLE ONLY archivecopyjob
    ADD CONSTRAINT archivecopyjob_targetcomponent_fk
    FOREIGN KEY (target_component) REFERENCES component(id);

-- Create new ArchiveCopyJobArch table.

-- Inter-archive package copy jobs can be source only or including binary
-- packages.

-- In the first case the user may want to specify a list of DistroArchSeries
-- for which Build records should be created after the source packages have
-- been copied.

-- In the second case the user may want to specify a list of DistroArchSeries
-- for which to copy the binary packages.

-- We will need to insert one ArchiveCopyJobArch row For each
-- DistroArchSeries specified.


CREATE TABLE archivecopyjobarch (
    -- The inter-archive package copy job in question.
    archivecopyjob integer NOT NULL,
    -- An architecture specified for the copy operation.
    distroarchseries integer NOT NULL
);

ALTER TABLE ONLY archivecopyjobarch
    ADD CONSTRAINT archivecopyjobarch__archivecopyjob__fk
    FOREIGN KEY (archivecopyjob) REFERENCES archive(id);
ALTER TABLE ONLY archivecopyjobarch
    ADD CONSTRAINT archivecopyjobarch__distroarchseries__fk
    FOREIGN KEY (distroarchseries) REFERENCES distroarchseries(id);

INSERT INTO LaunchpadDatabaseRevision VALUES (121, 99, 0);
