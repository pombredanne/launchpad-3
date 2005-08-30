DROP VIEW vsourcepackageindistro;

CREATE VIEW vsourcepackageindistro AS
SELECT sourcepackagerelease.id, sourcepackagerelease.manifest, sourcepackagerelease.format, 
       sourcepackagerelease.sourcepackagename, sourcepackagename.name, 
       sourcepackagepublishing.distrorelease, distrorelease.distribution,
       sourcepackagepublishing.status, sourcepackagepublishing.pocket
  FROM sourcepackagepublishing
  JOIN sourcepackagerelease ON sourcepackagepublishing.sourcepackagerelease = sourcepackagerelease.id
  JOIN distrorelease ON sourcepackagepublishing.distrorelease = distrorelease.id
  JOIN sourcepackagename ON sourcepackagerelease.sourcepackagename = sourcepackagename.id;

INSERT INTO LaunchpadDatabaseRevision VALUES (25, 66, 0);
