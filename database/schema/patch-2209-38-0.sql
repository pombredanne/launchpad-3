-- Copyright 2012 Canonical Ltd.  This software is licensed under the
-- GNU Affero General Public License version 3 (see the file LICENSE).

SET client_min_messages=ERROR;

CREATE TABLE LatestPublishedReleases (
    publication integer PRIMARY KEY,
    date_uploaded timestamp without time zone,
    creator integer NOT NULL,
    maintainer integer NOT NULL,
    archive_purpose integer NOT NULL,
    upload_archive integer NOT NULL,
    upload_distroseries integer NOT NULL,
    sourcepackagename integer NOT NULL,
    sourcepackagerelease integer NOT NULL
);


CREATE INDEX latestpublishedreleases__creator__idx
    ON LatestPublishedReleases USING btree (creator);

CREATE INDEX latestpublishedreleases__maintainer__idx
    ON LatestPublishedReleases USING btree (maintainer);

CREATE INDEX latestpublishedreleases__archive_purpose__idx
    ON LatestPublishedReleases USING btree (archive_purpose);

ALTER TABLE LatestPublishedReleases ADD CONSTRAINT upload_archive__upload_distroseries__sourcepackagename__key
     UNIQUE (upload_archive, upload_distroseries, sourcepackagename);

COMMENT ON TABLE LatestPublishedReleases IS 'LatestPublishedReleases: The most recent published source package releases for a given (distroseries, archive, sourcepackage).';
COMMENT ON COLUMN LatestPublishedReleases.upload_archive IS 'The target archive for the release.';
COMMENT ON COLUMN LatestPublishedReleases.sourcepackagename IS 'The SourcePackageName of the release.';
COMMENT ON COLUMN LatestPublishedReleases.upload_distroseries IS 'The distroseries into which the sourcepackagerelease was published.';
COMMENT ON COLUMN LatestPublishedReleases.sourcepackagerelease IS 'The sourcepackagerelease which was published.';
COMMENT ON COLUMN LatestPublishedReleases.archive_purpose IS 'The purpose of the archive, e.g. COMMERCIAL.  See the ArchivePurpose DBSchema item.';
COMMENT ON COLUMN LatestPublishedReleases.date_uploaded IS 'The date/time on which the source was actually published into the archive.';


CREATE TABLE GarboJobState (
    name text PRIMARY KEY,
    json_data text
);

COMMENT ON TABLE GarboJobState IS 'Contains persistent state for named garbo jobs.';
COMMENT ON COLUMN GarboJobState.name IS 'The name of the job.';
COMMENT ON COLUMN GarboJobState.json_data IS 'A JSON struct containing data for the job.';


INSERT INTO LaunchpadDatabaseRevision VALUES (2209, 38, 0);
