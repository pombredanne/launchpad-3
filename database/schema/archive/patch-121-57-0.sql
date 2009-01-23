SET client_min_messages=ERROR;

-- Replace current PackageUpload constraint with a more restricted one,
-- forcing single source uploads. This is not a model restriction, but
-- instead a ubuntu restriction, an upload can contain only *one* source
-- and one or more build results (security uploads) and one or more custom
-- files (translation, installer, dist-upgrader or ddtp-tarball).

ALTER TABLE PackageUploadSource DROP CONSTRAINT distroreleasequeuesource__distroreleasequeue__sourcepackagerelease;

ALTER TABLE PackageUploadSource ADD CONSTRAINT packageuploadsource__packageupload__key UNIQUE(packageupload);


INSERT INTO LaunchpadDatabaseRevision VALUES (121, 57, 0);
