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
    date_created timestamp without time zone
    DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'UTC') NOT NULL;

-- All copy archive workflows identified so far are tied to a single
-- distroseries. Since this is not necessarily the case for other archive
-- types the foreign key below is optional.
ALTER TABLE archive ADD COLUMN
    distroseries integer REFERENCES distroseries(id);

CREATE INDEX archive__distroseries__idx
    ON archive (distroseries)
    WHERE distroseries IS NOT NULL;

-- Create new ArchiveOperation table.

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

CREATE TABLE archiveoperation (
    id serial PRIMARY KEY,

    -- The archive operation type, may be one of:
    --  * copy source and binary
    --  * copy source only
    --  * cancel builds
    --  * resume (cancelled) builds
    --  * retry builds
    operation_type integer NOT NULL,

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

    -- The person who requested the archive operation.
    requester integer NOT NULL,
    -- The archive operation's status (new, in-progress, cancelled, succeeded,
    -- failed).
    status integer NOT NULL,
    -- The reason why this archive operation was requested (one-liner).
    reason text,

    -- Package copy operation only: the source archive from which packages are
    -- to be copied.
    source_archive integer,
    -- Package copy operation only: this is the source distroseries.
    source_distroseries integer,
    -- Package copy operation only: copy packages belonging to this component.
    source_component integer,
    -- Package copy operation only: copy packages belonging to this pocket.
    source_pocket integer,

    -- When was this archive operation requested?
    date_created timestamp without time zone
    DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'UTC') NOT NULL,
    -- When was this archive operation started?
    date_started timestamp without time zone
    DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'UTC') NOT NULL,
    -- When did this archive operation conclude?
    date_completed timestamp without time zone
    DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'UTC') NOT NULL
);

ALTER TABLE ONLY archiveoperation
    ADD CONSTRAINT archiveoperation__sourcearchive__fk
    FOREIGN KEY (source_archive) REFERENCES archive(id);

ALTER TABLE ONLY archiveoperation
    ADD CONSTRAINT archiveoperation_sourcecomponent_fk
    FOREIGN KEY (source_component) REFERENCES component(id);

ALTER TABLE ONLY archiveoperation
    ADD CONSTRAINT archiveoperation__targetarchive__fk
    FOREIGN KEY (target_archive) REFERENCES archive(id);

ALTER TABLE ONLY archiveoperation
    ADD CONSTRAINT archiveoperation_targetcomponent_fk
    FOREIGN KEY (target_component) REFERENCES component(id);

ALTER TABLE ONLY archiveoperation
    ADD CONSTRAINT archiveoperation_targetdistroseries_fk
    FOREIGN KEY (target_distroseries) REFERENCES distroseries(id);

ALTER TABLE ONLY archiveoperation
    ADD CONSTRAINT archiveoperation_sourcedistroseries_fk
    FOREIGN KEY (source_distroseries) REFERENCES distroseries(id);

ALTER TABLE ONLY archiveoperation
    ADD CONSTRAINT archiveoperation_requester_fk
    FOREIGN KEY (requester) REFERENCES person(id);

CREATE INDEX archiveoperation__targetarchive__idx
    ON archiveoperation (target_archive);

CREATE INDEX archiveoperation__requester__idx
    ON archiveoperation (requester);

CREATE INDEX archiveoperation__datecreated__idx
    ON archiveoperation (date_created);

CREATE INDEX archiveoperation__targetdistroseries__idx
    ON archiveoperation (target_distroseries)
    WHERE target_distroseries IS NOT NULL;

INSERT INTO LaunchpadDatabaseRevision VALUES (121, 99, 0);
