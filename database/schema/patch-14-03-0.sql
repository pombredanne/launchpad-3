SET client_min_messages=ERROR;

/*
 * Source Package Release History work
 */

CREATE TABLE SourcePackagePublishingHistory (
    id                    serial PRIMARY KEY,
    sourcepackagerelease  integer NOT NULL
            CONSTRAINT sourcepackagepublishinghistory_sourcepackagerelease_fk
            REFERENCES SourcePackageRelease,
    distrorelease         integer NOT NULL
            CONSTRAINT sourcepackagepublishinghistory_distrorelease_fk
            REFERENCES DistroRelease,
    status                integer NOT NULL, -- dbschema.PackagePublishingStatus
    component             integer NOT NULL
            CONSTRAINT sourcepackagepublishinghistory_component_fk
            REFERENCES Component,
    section               integer NOT NULL
            CONSTRAINT sourcepackagepublishinghistory_section_fk
            REFERENCES Section,
    datecreated           timestamp without time zone NOT NULL,
    datepublished         timestamp without time zone,
    datesuperseded        timestamp without time zone,
    supersededby          integer
            CONSTRAINT sourcepackagepublishinghistory_supersededby_fk
            REFERENCES SourcePackageRelease,
    datemadepending       timestamp without time zone,
    scheduleddeletiondate timestamp without time zone,
    dateremoved           timestamp without time zone
);	 

INSERT INTO LaunchpadDatabaseRevision VALUES (14,3,0);
