SET client_min_messages=ERROR;

-- Derived archives are generalized copy archives with a parent. We envision
-- they will be used for point releases, rebuilds, stable snapshots etc.

-- The concept of rebuild archives is being extended to generalised copy
-- archives.
-- Table 'archiverebuild' will hence be renamed to 'derivedarchive'.

-- Step 1: get rid of the old constraints
ALTER TABLE ONLY archiverebuild DROP
    CONSTRAINT archiverebuild__archive__key ;

ALTER TABLE ONLY archiverebuild DROP
    CONSTRAINT archiverebuild__archive__fk ;

ALTER TABLE ONLY archiverebuild DROP
    CONSTRAINT archiverebuild__distroseries__fk ;

ALTER TABLE ONLY archiverebuild DROP
    CONSTRAINT archiverebuild__requestor__fk ;

-- Step 2: rename the table and the associated index.
ALTER TABLE ONLY archiverebuild RENAME COLUMN status TO rebuild_status;
ALTER TABLE ONLY archiverebuild RENAME TO derivedarchive;

ALTER INDEX archiverebuild__registrant__idx RENAME TO
    derivedarchive__registrant__idx;

-- Step 3: now recreate the constraints with proper names
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

    -- This is the target archive to which packages are to be copied.
    target_archive integer NOT NULL,
    -- This is the target component.
    target_component integer NOT NULL,

    -- The person who requested the inter-archive package copy operation.
    registrant integer NOT NULL,
    -- The copy job's status (new, in-progress, cancelled, succeeded, failed).
    status integer NOT NULL,
    -- The reason why this copy job was requested (one-liner).
    reason text,

    -- When was this copy job requested?
    date_created timestamp without time zone
    DEFAULT timezone('UTC'::text, ('now'::text)::timestamp(6) with time zone)
    NOT NULL,
    -- When was this copy job started?
    date_started timestamp without time zone
    DEFAULT timezone('UTC'::text, ('now'::text)::timestamp(6) with time zone)
    NOT NULL,
    -- When did this copy job conclude?
    date_completed timestamp without time zone
    DEFAULT timezone('UTC'::text, ('now'::text)::timestamp(6) with time zone)
    NOT NULL
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

INSERT INTO LaunchpadDatabaseRevision VALUES (121, 81, 0);
