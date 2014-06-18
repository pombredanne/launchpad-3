-- Copyright 2014 Canonical Ltd.  This software is licensed under the
-- GNU Affero General Public License version 3 (see the file LICENSE).

SET client_min_messages=ERROR;

CREATE TABLE LiveFS (
    id serial PRIMARY KEY,
    date_created timestamp without time zone DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'UTC') NOT NULL,
    date_last_modified timestamp without time zone DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'UTC') NOT NULL,
    registrant integer NOT NULL REFERENCES person,
    owner integer NOT NULL REFERENCES person,
    distro_series integer NOT NULL REFERENCES distroseries,
    name text NOT NULL,
    json_data text,
    require_virtualized boolean DEFAULT true NOT NULL,
    CONSTRAINT valid_name CHECK (valid_name(name)),
    CONSTRAINT livefs__owner__distro_series__name__key UNIQUE (owner, distro_series, name)
);

COMMENT ON TABLE LiveFS IS 'A class of buildable live filesystem images.  Rows in this table only partially define how to build an image; the rest of the information comes from LiveFSBuild.';
COMMENT ON COLUMN LiveFS.registrant IS 'The user who registered the live filesystem image.';
COMMENT ON COLUMN LiveFS.owner IS 'The owner of the live filesystem image.';
COMMENT ON COLUMN LiveFS.distro_series IS 'The DistroSeries for which the image should be built.';
COMMENT ON COLUMN LiveFS.name IS 'The name of the live filesystem image, unique per DistroSeries.';
COMMENT ON COLUMN LiveFS.json_data IS 'A JSON struct containing data for the image build.';
COMMENT ON COLUMN LiveFS.require_virtualized IS 'If True, this live filesystem image must be built only on a virtual machine.';

CREATE INDEX livefs__registrant__idx
    ON LiveFS (registrant);
CREATE INDEX livefs__owner__idx
    ON LiveFS (owner);
CREATE INDEX livefs__distro_series__idx
    ON LiveFS (distro_series);
CREATE INDEX livefs__name__idx
    ON LiveFS (name);

CREATE TABLE LiveFSBuild (
    id serial PRIMARY KEY,
    requester integer NOT NULL REFERENCES person,
    livefs integer NOT NULL REFERENCES livefs,
    archive integer NOT NULL REFERENCES archive,
    distro_arch_series integer NOT NULL REFERENCES distroarchseries,
    pocket integer NOT NULL,
    unique_key text,
    json_data_override text,
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

COMMENT ON TABLE LiveFSBuild IS 'A build record for a live filesystem image.';
COMMENT ON COLUMN LiveFSBuild.requester IS 'The person who requested this live filesystem image build.';
COMMENT ON COLUMN LiveFSBuild.livefs IS 'Live filesystem image to build.';
COMMENT ON COLUMN LiveFSBuild.archive IS 'The archive that the live filesystem image should build from.';
COMMENT ON COLUMN LiveFSBuild.distro_arch_series IS 'The distroarchseries that the live filesystem image should build from.';
COMMENT ON COLUMN LiveFSBuild.pocket IS 'The pocket that the live filesystem image should build from.';
COMMENT ON COLUMN LiveFSBuild.unique_key IS 'A unique key distinguishing this build from others for the same livefs/archive/distroarchseries/pocket, or NULL.';
COMMENT ON COLUMN LiveFSBuild.json_data_override IS 'A JSON struct containing data for the image build, each key of which overrides the same key from livefs.json_data.';
COMMENT ON COLUMN LiveFSBuild.virtualized IS 'The virtualization setting required by this build farm job.';
COMMENT ON COLUMN LiveFSBuild.date_created IS 'When the build farm job record was created.';
COMMENT ON COLUMN LiveFSBuild.date_started IS 'When the build farm job started being processed.';
COMMENT ON COLUMN LiveFSBuild.date_finished IS 'When the build farm job finished being processed.';
COMMENT ON COLUMN LiveFSBuild.date_first_dispatched IS 'The instant the build was dispatched the first time.  This value will not get overridden if the build is retried.';
COMMENT ON COLUMN LiveFSBuild.builder IS 'The builder which processed this build farm job.';
COMMENT ON COLUMN LiveFSBuild.status IS 'The current build status.';
COMMENT ON COLUMN LiveFSBuild.log IS 'The log file for this build farm job stored in the librarian.';
COMMENT ON COLUMN LiveFSBuild.upload_log IS 'The upload log file for this build farm job stored in the librarian.';
COMMENT ON COLUMN LiveFSBuild.dependencies IS 'A Debian-like dependency line specifying the current missing dependencies for this build.';
COMMENT ON COLUMN LiveFSBuild.failure_count IS 'The number of consecutive failures on this job.  If excessive, the job may be terminated.';
COMMENT ON COLUMN LiveFSBuild.build_farm_job IS 'The build farm job with the base information.';

CREATE INDEX livefsbuild__requester__idx
    ON LiveFSBuild (requester);
CREATE INDEX livefsbuild__livefs__idx
    ON LiveFSBuild (livefs);
CREATE INDEX livefsbuild__archive__idx
    ON LiveFSBuild (archive);
CREATE INDEX livefsbuild__distro_arch_series__idx
    ON LiveFSBuild (distro_arch_series);
CREATE INDEX livefsbuild__log__idx
    ON LiveFSBuild (log);
CREATE INDEX livefsbuild__upload_log__idx
    ON LiveFSBuild (upload_log);
CREATE INDEX livefsbuild__build_farm_job__idx
    ON LiveFSBuild (build_farm_job);

-- LiveFS.requestBuild
CREATE INDEX livefsbuild__livefs__archive__das__pocket__unique_key__status__idx
    ON LiveFSBuild (
        livefs, archive, distro_arch_series, pocket, unique_key, status);

-- LiveFS.builds, LiveFS.completed_builds, LiveFS.pending_builds
CREATE INDEX livefsbuild__livefs__status__started__finished__created__id__idx
    ON LiveFSBuild (
        livefs, status, GREATEST(date_started, date_finished) DESC,
        date_created DESC, id DESC);

-- LiveFSBuild.getMedianBuildDuration
CREATE INDEX livefsbuild__livefs__das__status__finished__idx
    ON LiveFSBuild (livefs, distro_arch_series, status, date_finished DESC)
    -- 1 == FULLYBUILT
    WHERE status = 1;

CREATE TABLE LiveFSFile (
    id serial PRIMARY KEY,
    livefsbuild integer NOT NULL REFERENCES livefsbuild,
    libraryfile integer NOT NULL REFERENCES libraryfilealias
);

COMMENT ON TABLE LiveFSFile IS 'A link between a live filesystem build and a file in the librarian that it produces.';
COMMENT ON COLUMN LiveFSFile.livefsbuild IS 'The live filesystem build producing this file.';
COMMENT ON COLUMN LiveFSFile.libraryfile IS 'A file in the librarian.';

CREATE INDEX livefsfile__livefsbuild__idx
    ON LiveFSFile (livefsbuild);

INSERT INTO LaunchpadDatabaseRevision VALUES (2209, 56, 0);
