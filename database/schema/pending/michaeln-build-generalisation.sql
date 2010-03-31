-- Copyright 2010 Canonical Ltd.  This software is licensed under the
-- GNU Affero General Public License version 3 (see the file LICENSE).

SET client_min_messages=ERROR;

-- The schema patch for general build histories. See
-- https://dev.launchpad.net/LEP/GeneralBuildHistories and the linked
-- blueprint/bug for more information.

-- Still to do:
--   Inventory check of all table columns to ensure nothing is lost
--   Replicate current indexes/foreign key constraints (as noted below)
--   Populate with any (future) SPRecipeBuild data (as noted below)
--   Update all sample data :(

-- Step 1
-- Create the new BuildFarmJob table using current data from binary
-- builds, with it's own new primary key (as we'll use Build.id for the
-- BinaryPackageBuild table).
CREATE SEQUENCE buildfarmjob_id;
CREATE TABLE BuildFarmJob AS
    SELECT
        nextval('buildfarmjob_id') AS id,
        build.processor,
        archive.require_virtualized AS virtualised,
        -- Currently we do not know if a build was virtual or not? (it's only
        -- on the archive and the builder, both of which can change).
        -- IBuild.is_virtualized just queries the archive.
        buildqueue.estimated_duration,
        buildqueue.lastscore AS score,
        build.datecreated AS date_created,
        (build.datebuilt - build.buildduration) AS date_started,
        build.datebuilt AS date_finished,
        build.builder,
        build.buildstate AS status,
        buildqueue.logtail AS log_tail,
        build.buildlog AS log,
        build.id AS build_id -- Temporary reference that will be removed below.
    FROM
       build LEFT JOIN buildpackagejob ON build.id = buildpackagejob.build
             LEFT JOIN buildqueue ON buildqueue.job = buildpackagejob.job,
       archive
    WHERE
       build.archive = archive.id;

ALTER SEQUENCE buildfarmjob_id OWNED BY BuildFarmJob.id;
ALTER TABLE buildfarmjob ALTER id SET DEFAULT nextval('buildfarmjob_id');
ALTER TABLE buildfarmjob ADD PRIMARY KEY (id);
-- TODO: Replicate indexes and foreign key constraints.
-- TODO: Add any data from current SourcePackageRecipeBuild records.

-- Step 2
-- Create the PackageBuild table for information specific to builds of
-- packages that will end up being published in archives.
CREATE SEQUENCE packagebuild_id;
CREATE TABLE PackageBuild AS
    SELECT
        nextval('packagebuild_id') AS id,
        buildfarmjob.id AS build_farm_job,
        build.archive,
        build.pocket,
        build.upload_log,
        build.dependencies
    FROM
        build JOIN buildfarmjob ON build.id = buildfarmjob.build_id;
ALTER TABLE packagebuild ALTER id SET DEFAULT nextval('packagebuild_id');
ALTER TABLE packagebuild ADD PRIMARY KEY (id);
-- TODO: Replicate indexes and foreign key constraints.
-- TODO: Add any data from current SPRecipeBuild records.

-- Step 3
-- Create the BinaryPackageBuild table for information specific to binary
-- package builds.
CREATE SEQUENCE binarypackagebuild_id;
CREATE TABLE BinaryPackageBuild AS
    SELECT
        nextval('binarypackagebuild_id') AS id,
        packagebuild.id AS package_build,
        build.distroarchseries AS distro_arch_series,
        build.sourcepackagerelease AS source_package_release,
        build.build_warnings -- We don't seem to use this in LP code at all?
    FROM
        build JOIN buildfarmjob ON build.id = buildfarmjob.build_id
              JOIN packagebuild ON packagebuild.build_farm_job = buildfarmjob.id;
ALTER TABLE binarypackagebuild ALTER id SET DEFAULT nextval('binarypackagebuild_id');
ALTER TABLE binarypackagebuild ADD PRIMARY KEY (id);
-- TODO: Replicate indexes and foreign key constraints.

-- Step 4
-- Update the SourcePackageRecipeBuild table with a package_build foreign key
-- to PackageBuild and remove the unnecessary columns.

-- Step 5
-- Create an empty TranslationTemplatesBuild table (talk with jtv about this).

-- Step 6
-- Note, to enable parallel development getting the codebase updated, we may
-- want to do the following cleanup in a subsequent branch (in the same pipe
-- of course) so we can gradually move the code over to the new schema without
-- breaking all the tests.
-- Data cleanup. We need to:
--   1. Remove the temporary build_id column on BuildFarmJob
--   2. Remove the build table (TODO: check for other references to build and
--      update them to BinaryPackageBuild.id)
--   3. Remove current buildqueue table.
--   4. Remove related job records
--   5. Remove the BuildPackageJob table.

