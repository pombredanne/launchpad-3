SET client_min_messages = ERROR;

drop view sourcepackagepublishingview;
drop view binarypackagepublishingview;

drop view sourcepackagefilepublishing;
drop view binarypackagefilepublishing;

drop view publishedpackageview;

drop view sourcepackagepublishing;
drop view binarypackagepublishing;

CREATE VIEW sourcepackagefilepublishing AS
  SELECT 
    (((libraryfilealias.id)::text || '.'::text) || (sourcepackagepublishinghistory.id)::text) AS id,
    distrorelease.distribution,
    sourcepackagepublishinghistory.id AS sourcepackagepublishing,
    sourcepackagereleasefile.libraryfile AS libraryfilealias,
    libraryfilealias.filename AS libraryfilealiasfilename,
    sourcepackagename.name AS sourcepackagename,
    component.name AS componentname,
    distrorelease.name AS distroreleasename,
    sourcepackagepublishinghistory.status AS publishingstatus,
    sourcepackagepublishinghistory.pocket
  FROM ((((((
    sourcepackagepublishinghistory
    JOIN sourcepackagerelease ON ((sourcepackagepublishinghistory.sourcepackagerelease = sourcepackagerelease.id)))
    JOIN sourcepackagename ON ((sourcepackagerelease.sourcepackagename = sourcepackagename.id)))
    JOIN sourcepackagereleasefile ON ((sourcepackagereleasefile.sourcepackagerelease = sourcepackagerelease.id)))
    JOIN libraryfilealias ON ((libraryfilealias.id = sourcepackagereleasefile.libraryfile)))
    JOIN distrorelease ON ((sourcepackagepublishinghistory.distrorelease = distrorelease.id)))
    JOIN component ON ((sourcepackagepublishinghistory.component = component.id)));

CREATE VIEW binarypackagefilepublishing AS
  SELECT
    (((libraryfilealias.id)::text || '.'::text) || (binarypackagepublishinghistory.id)::text) AS id,
    distrorelease.distribution,
    binarypackagepublishinghistory.id AS binarypackagepublishing,
    component.name AS componentname,
    libraryfilealias.filename AS libraryfilealiasfilename,
    sourcepackagename.name AS sourcepackagename,
    binarypackagefile.libraryfile AS libraryfilealias,
    distrorelease.name AS distroreleasename,
    distroarchrelease.architecturetag,
    binarypackagepublishinghistory.status AS publishingstatus,
    binarypackagepublishinghistory.pocket
  FROM (((((((((
    binarypackagepublishinghistory
    JOIN binarypackagerelease ON ((binarypackagepublishinghistory.binarypackagerelease = binarypackagerelease.id)))
    JOIN build ON ((binarypackagerelease.build = build.id)))
    JOIN sourcepackagerelease ON ((build.sourcepackagerelease = sourcepackagerelease.id)))
    JOIN sourcepackagename ON ((sourcepackagerelease.sourcepackagename = sourcepackagename.id)))
    JOIN binarypackagefile ON ((binarypackagefile.binarypackagerelease = binarypackagerelease.id)))
    JOIN libraryfilealias ON ((binarypackagefile.libraryfile = libraryfilealias.id)))
    JOIN distroarchrelease ON ((binarypackagepublishinghistory.distroarchrelease = distroarchrelease.id)))
    JOIN distrorelease ON ((distroarchrelease.distrorelease = distrorelease.id)))
    JOIN component ON ((binarypackagepublishinghistory.component = component.id)));

CREATE VIEW publishedpackageview AS
  SELECT
    binarypackagepublishinghistory.id,
    distroarchrelease.id AS distroarchrelease,
    distrorelease.distribution,
    distrorelease.id AS distrorelease,
    distrorelease.name AS distroreleasename,
    processorfamily.id AS processorfamily,
    processorfamily.name AS processorfamilyname,
    binarypackagepublishinghistory.status AS packagepublishingstatus,
    component.name AS component,
    section.name AS section,
    binarypackagerelease.id AS binarypackagerelease,
    binarypackagename.name AS binarypackagename,
    binarypackagerelease.summary AS binarypackagesummary,
    binarypackagerelease.description AS binarypackagedescription,
    binarypackagerelease.version AS binarypackageversion,
    build.id AS build,
    build.datebuilt,
    sourcepackagerelease.id AS sourcepackagerelease,
    sourcepackagerelease.version AS sourcepackagereleaseversion,
    sourcepackagename.name AS sourcepackagename,
    binarypackagepublishinghistory.pocket,
    binarypackagerelease.fti AS binarypackagefti
  FROM ((((((((((
    binarypackagepublishinghistory
    JOIN distroarchrelease ON ((distroarchrelease.id = binarypackagepublishinghistory.distroarchrelease)))
    JOIN distrorelease ON ((distroarchrelease.distrorelease = distrorelease.id)))
    JOIN processorfamily ON ((distroarchrelease.processorfamily = processorfamily.id)))
    JOIN component ON ((binarypackagepublishinghistory.component = component.id)))
    JOIN binarypackagerelease ON ((binarypackagepublishinghistory.binarypackagerelease = binarypackagerelease.id)))
    JOIN section ON ((binarypackagepublishinghistory.section = section.id)))
    JOIN binarypackagename ON ((binarypackagerelease.binarypackagename = binarypackagename.id)))
    JOIN build ON ((binarypackagerelease.build = build.id)))
    JOIN sourcepackagerelease ON ((build.sourcepackagerelease = sourcepackagerelease.id)))
    JOIN sourcepackagename ON ((sourcepackagerelease.sourcepackagename = sourcepackagename.id)));

INSERT INTO LaunchpadDatabaseRevision VALUES (67, 14, 0);
