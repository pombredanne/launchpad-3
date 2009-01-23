SET client_min_messages=ERROR;

-- The concept of rebuild archives is being extended to generalized copy
-- archives.

-- Table 'archiverebuild' will hence be dropped. Some of the columns needed
-- for copy archives are of general interest and will be added to the archive
-- table proper.

-- Step 1: get rid of the old table ('archiverebuild')
DROP TABLE archiverebuild;

-- We want to be able to capture archive creation times.
ALTER TABLE archive ADD COLUMN
    date_created timestamp without time zone;

UPDATE archive SET date_created = (
    SELECT MIN(datecreated)
    FROM securesourcepackagepublishinghistory
    WHERE securesourcepackagepublishinghistory.archive = archive.id);

UPDATE archive SET date_created = date_updated WHERE date_created IS NULL;
UPDATE archive SET date_created = date_updated where date_updated < date_created;

ALTER TABLE archive ALTER COLUMN date_created
    SET DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'UTC');
ALTER TABLE archive ALTER COLUMN date_created SET NOT NULL;

-- Create new PackageCopyRequest table.

-- Once an archive has been put into place the user will want to carry
-- out certain operations on it like e.g.

--   * copy packages to it; some workflows may well result in multiple copy
--     operations.
--   * cancel or resume builds given an archive/distroseries/component/pocket
--   * retry failed builds given an archive/distroseries/component/pocket

-- These archive level operations may take quite a bit of time and should
-- not be tied to a web GUI request because the latter is likely to time
-- out.

-- Instead the user will *specify* the operation he wants performed on an
-- archive along with any parameters needed. That will be picked up by a
-- service and performed in the background.

-- The GUI will facilitate the monitoring (progress) and manipulation
-- (cancellation) of these archive operations

-- For now we introduce the PackageCopyRequest since this is what we need to
-- get the rebuild archives and snapshots working.

CREATE TABLE PackageCopyRequest (
    id serial PRIMARY KEY,

    -- Please note: the user may use a number of optional "filters" (e.g.
    -- target distroseries, component, pocket) in order to define the scope
    -- for the archive operation on hand.
    -- If neither of these are set, the operation will apply to the target
    -- archive at large.

    -- This is the target archive to which this operation applies.
    target_archive integer NOT NULL,
    -- This is the target distroseries.
    target_distroseries integer,
    -- This is the target component.
    target_component integer,
    -- This is the target pocket.
    target_pocket integer,

    -- Whether binary packages should be copied.
    copy_binaries boolean default False NOT NULL,

    -- The source archive from which packages are to be copied.
    source_archive integer NOT NULL,
    -- This is the source distroseries.
    source_distroseries integer,
    -- Copy packages belonging to this component.
    source_component integer,
    -- Copy packages belonging to this pocket.
    source_pocket integer,

    -- The person who requested the archive operation.
    requester integer NOT NULL,
    -- The archive operation's status (new, in-progress, complete, failed,
    -- cancelling, cancelled).
    status integer NOT NULL,
    -- The reason why this archive operation was requested (one-liner).
    reason text,

    -- When was this archive operation requested?
    date_created timestamp without time zone
    DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'UTC') NOT NULL,
    -- When was this archive operation started?
    date_started timestamp without time zone,
    -- When did this archive operation conclude?
    date_completed timestamp without time zone
);

ALTER TABLE ONLY packagecopyrequest
    ADD CONSTRAINT packagecopyrequest__sourcearchive__fk
    FOREIGN KEY (source_archive) REFERENCES archive(id);

ALTER TABLE ONLY packagecopyrequest
    ADD CONSTRAINT packagecopyrequest_sourcecomponent_fk
    FOREIGN KEY (source_component) REFERENCES component(id);

ALTER TABLE ONLY packagecopyrequest
    ADD CONSTRAINT packagecopyrequest__targetarchive__fk
    FOREIGN KEY (target_archive) REFERENCES archive(id);

ALTER TABLE ONLY packagecopyrequest
    ADD CONSTRAINT packagecopyrequest_targetcomponent_fk
    FOREIGN KEY (target_component) REFERENCES component(id);

ALTER TABLE ONLY packagecopyrequest
    ADD CONSTRAINT packagecopyrequest_targetdistroseries_fk
    FOREIGN KEY (target_distroseries) REFERENCES distroseries(id);

ALTER TABLE ONLY packagecopyrequest
    ADD CONSTRAINT packagecopyrequest_sourcedistroseries_fk
    FOREIGN KEY (source_distroseries) REFERENCES distroseries(id);

ALTER TABLE ONLY packagecopyrequest
    ADD CONSTRAINT packagecopyrequest_requester_fk
    FOREIGN KEY (requester) REFERENCES person(id);

CREATE INDEX packagecopyrequest__targetarchive__idx
    ON packagecopyrequest (target_archive);

CREATE INDEX packagecopyrequest__requester__idx
    ON packagecopyrequest (requester);

CREATE INDEX packagecopyrequest__datecreated__idx
    ON packagecopyrequest (date_created);

CREATE INDEX packagecopyrequest__targetdistroseries__idx
    ON packagecopyrequest (target_distroseries)
    WHERE target_distroseries IS NOT NULL;

-- Create table ArchiveArch

-- This table allows a user to specify which architectures an archive
-- requires or supports. There will be one row per archive/architecture
-- combination.

-- In case where architectures are specified for an archive in conjunction
-- with e.g. a distroseries, the intersection between the archive's
-- architectures and the appropriate distroarchseries' will determine what
-- builds/binary packages are supported in the archive.

CREATE TABLE archivearch (
    id serial PRIMARY KEY,
    archive integer NOT NULL,
    processorfamily integer NOT NULL
);

ALTER TABLE ONLY archivearch
    ADD CONSTRAINT archivearch__archive__fk FOREIGN KEY (archive) REFERENCES archive(id);

ALTER TABLE ONLY archivearch
    ADD CONSTRAINT archivearch__processorfamily__fk FOREIGN KEY (processorfamily) REFERENCES processorfamily(id);

ALTER TABLE ONLY archivearch
    ADD CONSTRAINT archivearch__processorfamily__archive__key UNIQUE (processorfamily, archive);

INSERT INTO LaunchpadDatabaseRevision VALUES (121, 85, 0);
