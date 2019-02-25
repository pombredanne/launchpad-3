-- Copyright 2015 Canonical Ltd.  This software is licensed under the
-- GNU Affero General Public License version 3 (see the file LICENSE).

SET client_min_messages=ERROR;

CREATE TABLE Snap (
    id serial PRIMARY KEY,
    date_created timestamp without time zone DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'UTC') NOT NULL,
    date_last_modified timestamp without time zone DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'UTC') NOT NULL,
    registrant integer NOT NULL REFERENCES person,
    owner integer NOT NULL REFERENCES person,
    distro_series integer NOT NULL REFERENCES distroseries,
    name text NOT NULL,
    description text,
    branch integer REFERENCES branch,
    git_repository integer REFERENCES gitrepository,
    git_path text,
    require_virtualized boolean DEFAULT true NOT NULL,
    CONSTRAINT valid_name CHECK (valid_name(name)),
    CONSTRAINT consistent_git_ref CHECK ((git_repository IS NULL) = (git_path IS NULL)),
    CONSTRAINT consistent_vcs CHECK (null_count(ARRAY[branch, git_repository]) >= 1),
    CONSTRAINT snap__owner__name__key UNIQUE (owner, name)
);

COMMENT ON TABLE Snap IS 'A snap package.';
COMMENT ON COLUMN Snap.registrant IS 'The user who registered the snap package.';
COMMENT ON COLUMN Snap.owner IS 'The owner of the snap package.';
COMMENT ON COLUMN Snap.distro_series IS 'The DistroSeries for which the snap package should be built.';
COMMENT ON COLUMN Snap.name IS 'The name of the snap package, unique per owner and DistroSeries.';
COMMENT ON COLUMN Snap.description IS 'A description of the snap package.';
COMMENT ON COLUMN Snap.branch IS 'A Bazaar branch containing a snap recipe.';
COMMENT ON COLUMN Snap.git_repository IS 'A Git repository with a branch containing a snap recipe.';
COMMENT ON COLUMN Snap.git_path IS 'The path of the Git branch containing a snap recipe.';
COMMENT ON COLUMN Snap.require_virtualized IS 'If True, this snap package must be built only on a virtual machine.';

CREATE INDEX snap__registrant__idx
    ON Snap (registrant);
CREATE INDEX snap__distro_series__idx
    ON Snap (distro_series);
CREATE INDEX snap__branch__idx
    ON Snap (branch);
CREATE INDEX snap__git_repository__idx
    ON Snap (git_repository);

CREATE TABLE SnapArch (
    snap integer NOT NULL REFERENCES snap,
    processor integer NOT NULL REFERENCES processor,
    PRIMARY KEY (snap, processor)
);

COMMENT ON TABLE SnapArch IS 'The architectures a snap package should be built for.';
COMMENT ON COLUMN SnapArch.snap IS 'The snap package for which an architecture is specified.';
COMMENT ON COLUMN SnapArch.processor IS 'The architecture for which the snap package should be built.';

CREATE TABLE SnapBuild (
    id serial PRIMARY KEY,
    requester integer NOT NULL REFERENCES person,
    snap integer NOT NULL REFERENCES snap,
    archive integer NOT NULL REFERENCES archive,
    distro_arch_series integer NOT NULL REFERENCES distroarchseries,
    pocket integer NOT NULL,
    processor integer NOT NULL REFERENCES processor,
    virtualized boolean NOT NULL,
    date_created timestamp without time zone DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'UTC') NOT NULL,
    date_started timestamp without time zone,
    date_finished timestamp without time zone,
    date_first_dispatched timestamp without time zone,
    builder integer REFERENCES builder,
    status integer NOT NULL,
    log integer REFERENCES libraryfilealias,
    upload_log integer REFERENCES libraryfilealias,
    dependencies text,
    failure_count integer DEFAULT 0 NOT NULL,
    build_farm_job integer NOT NULL REFERENCES buildfarmjob
);

COMMENT ON TABLE SnapBuild IS 'A build record for a snap package.';
COMMENT ON COLUMN SnapBuild.requester IS 'The person who requested this snap package build.';
COMMENT ON COLUMN SnapBuild.snap IS 'The snap package to build.';
COMMENT ON COLUMN SnapBuild.archive IS 'The archive that the snap package should build from.';
COMMENT ON COLUMN SnapBuild.distro_arch_series IS 'The distroarchseries that the snap package should build from.';
COMMENT ON COLUMN SnapBuild.pocket IS 'The pocket that the snap package should build from.';
COMMENT ON COLUMN SnapBuild.virtualized IS 'The virtualization setting required by this build farm job.';
COMMENT ON COLUMN SnapBuild.date_created IS 'When the build farm job record was created.';
COMMENT ON COLUMN SnapBuild.date_started IS 'When the build farm job started being processed.';
COMMENT ON COLUMN SnapBuild.date_finished IS 'When the build farm job finished being processed.';
COMMENT ON COLUMN SnapBuild.date_first_dispatched IS 'The instant the build was dispatched the first time.  This value will not get overridden if the build is retried.';
COMMENT ON COLUMN SnapBuild.builder IS 'The builder which processed this build farm job.';
COMMENT ON COLUMN SnapBuild.status IS 'The current build status.';
COMMENT ON COLUMN SnapBuild.log IS 'The log file for this build farm job stored in the librarian.';
COMMENT ON COLUMN SnapBuild.upload_log IS 'The upload log file for this build farm job stored in the librarian.';
COMMENT ON COLUMN SnapBuild.dependencies IS 'A Debian-like dependency line specifying the current missing dependencies for this build.';
COMMENT ON COLUMN SnapBuild.failure_count IS 'The number of consecutive failures on this job.  If excessive, the job may be terminated.';
COMMENT ON COLUMN SnapBuild.build_farm_job IS 'The build farm job with the base information.';

CREATE INDEX snapbuild__requester__idx
    ON SnapBuild (requester);
CREATE INDEX snapbuild__snap__idx
    ON SnapBuild (snap);
CREATE INDEX snapbuild__archive__idx
    ON SnapBuild (archive);
CREATE INDEX snapbuild__distro_arch_series__idx
    ON SnapBuild (distro_arch_series);
CREATE INDEX snapbuild__log__idx
    ON SnapBuild (log);
CREATE INDEX snapbuild__upload_log__idx
    ON SnapBuild (upload_log);
CREATE INDEX snapbuild__build_farm_job__idx
    ON SnapBuild (build_farm_job);

-- Snap.requestBuild
CREATE INDEX snapbuild__snap__archive__das__pocket__status__idx
    ON SnapBuild (snap, archive, distro_arch_series, pocket, status);

-- Snap.builds, Snap.completed_builds, Snap.pending_builds
CREATE INDEX snapbuild__snap__status__started__finished__created__id__idx
    ON SnapBuild (
        snap, status, GREATEST(date_started, date_finished) DESC NULLS LAST,
        date_created DESC, id DESC);

-- SnapBuild.getMedianBuildDuration
CREATE INDEX snapbuild__snap__das__status__finished__idx
    ON SnapBuild (snap, distro_arch_series, status, date_finished DESC)
    -- 1 == FULLYBUILT
    WHERE status = 1;

CREATE TABLE SnapFile (
    id serial PRIMARY KEY,
    snapbuild integer NOT NULL REFERENCES snapbuild,
    libraryfile integer NOT NULL REFERENCES libraryfilealias
);

COMMENT ON TABLE SnapFile IS 'A link between a snap package build and a file in the librarian that it produces.';
COMMENT ON COLUMN SnapFile.snapbuild IS 'The snap package build producing this file.';
COMMENT ON COLUMN SnapFile.libraryfile IS 'A file in the librarian.';

CREATE INDEX snapfile__snapbuild__idx
    ON SnapFile (snapbuild);

INSERT INTO LaunchpadDatabaseRevision VALUES (2209, 69, 0);
