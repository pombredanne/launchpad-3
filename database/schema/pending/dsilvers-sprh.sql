/*
 * Source Package Release History work
 */

CREATE TABLE SourcePackagePublishingHistory (
    id                    serial PRIMARY KEY,
    sourcepackagerelease  integer NOT NULL REFERENCES SourcePackageRelease,
    distrorelease         integer NOT NULL REFERENCES DistroRelease,
    status                integer, -- from dbschema.PackagePublishingStatus
    component             integer NOT NULL REFERENCES Component,
    section               integer NOT NULL REFERENCES Section,
    datecreated           timestamp without time zone,
    datepublished         timestamp without time zone,
    datesuperseded        timestamp without time zone,
    supersededby          integer REFERENCES SourcePackageRelease,
    datemadepending       timestamp without time zone,
    scheduleddeletiondate timestamp without time zone,
    dateremoved           timestamp without time zone
);	 

COMMENT ON TABLE SourcePackagePublishingHistory IS 'SourcePackagePublishingHistory: The history of a SourcePackagePublishing record. This table represents the lifetime of a publishing record from inception to deletion. Records are never removed from here and in time the publishing table may become a view onto this table. A column being NULL indicates there''s no data for that state transition. E.g. a package which is removed without being superseded won''t have datesuperseded or supersededby filled in.';
COMMENT ON COLUMN SourcePackagePublishingHistory.sourcepackagerelease IS 'The sourcepackagerelease being published.';
COMMENT ON COLUMN SourcePackagePublishingHistory.distrorelease IS 'The distrorelease into which the sourcepackagerelease is being published.';
COMMENT ON COLUMN SourcePackagePublishingHistory.status IS 'The current status of the publishing.';
COMMENT ON COLUMN SourcePackagePublishingHistory.component IS 'The component into which the publishing takes place.';
COMMENT ON COLUMN SourcePackagePublishingHistory.section IS 'The section into which the publishing takes place.';
COMMENT ON COLUMN SourcePackagePublishingHistory.datecreated IS 'The date/time on which the publishing record was created.';
COMMENT ON COLUMN SourcePackagePublishingHistory.datepublished IS 'The date/time on which the source was actually published into an archive.';
COMMENT ON COLUMN SourcePackagePublishingHistory.datesuperseded IS 'The date/time on which the source was superseded by a new source.';
COMMENT ON COLUMN SourcePackagePublishingHistory.supersededby IS 'The source which superseded this one.';
COMMENT ON COLUMN SourcePackagePublishingHistory.datemadepending IS 'The date/time on which this publishing record was made to be pending removal from the archive.';
COMMENT ON COLUMN SourcePackagePublishingHistory.scheduleddeletiondate IS 'The date/time at which the source is/was scheduled to be deleted.';
COMMENT ON COLUMN SourcePackagePublishingHistory.dateremoved IS 'The date/time at which the source was actually deleted.';
