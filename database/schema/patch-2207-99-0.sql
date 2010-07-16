-- Copyright 2010 Canonical Ltd. This software is licensed under the
-- GNU Affero General Public License version 3 (see the file LICENSE).

SET client_min_messages=ERROR;

CREATE TEMPORARY TABLE NewBuildFarmJob AS SELECT
  nextval('buildfarmjob_id_seq') AS id, 1 AS processor, True AS virtualized, date_created, date_built - build_duration AS date_started, date_built AS date_finished, date_first_dispatched, builder, build_state, build_log, 3 AS job_type, id AS sprb_id FROM SourcePackageRecipeBuild;

INSERT INTO BuildFarmJob SELECT id, processor, virtualized, date_created, date_started, date_finished, date_first_dispatched, builder, build_state, build_log, job_type FROM NewBuildFarmJob;

CREATE TEMPORARY TABLE NewPackageBuild AS SELECT
  nextval('packagebuild_id_seq') AS id, NewBuildFarmJob.id AS new_build_farm_job, archive, pocket, upload_log, dependencies, SourcePackageRecipeBuild.id AS sprb_id FROM SourcePackageRecipeBuild, NewBuildFarmJob;

ALTER TABLE SourcePackageRecipeBuild
  ADD COLUMN package_build INTEGER REFERENCES PackageBuild NOT NULL;

UPDATE SourcePackageRecipebuild
  SET package_build=NewPackageBuild.id
  FROM NewPackageBuild
  WHERE sprb_id = SourcePackageRecipeBuild.id;

ALTER TABLE SourcePackageRecipeBuild
  ALTER COLUMN package_build SET NOT NULL, DROP COLUMN date_created,
  DROP COLUMN build_duration, DROP COLUMN date_built,
  DROP COLUMN date_first_dispatched, DROP COLUMN builder,
  DROP COLUMN build_state, DROP COLUMN build_log, DROP COLUMN archive,
  DROP COLUMN pocket, DROP COLUMN upload_log, DROP COLUMN dependencies;

INSERT INTO LaunchpadDatabaseRevision VALUES (2207, 99, 0);
