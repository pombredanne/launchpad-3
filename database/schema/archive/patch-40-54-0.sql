set client_min_messages=ERROR;

/* Rosetta Template Priorities

   Keep track of which templates are more important than others for
   translation purposes.
*/

UPDATE POTemplate SET priority=0 WHERE priority IS NULL;
ALTER TABLE POTemplate ALTER COLUMN priority SET DEFAULT 0;
ALTER TABLE POTemplate ALTER COLUMN priority SET NOT NULL;

-- Data migration removed as this patch takes several hours to run on
-- production data.

/* Give middle priority to the packages that are not part of language packs */
/*
UPDATE POTemplate
SET priority = 50
FROM sourcepackagefilepublishing, sourcepackagepublishing, distrorelease, sourcepackagename
WHERE
    sourcepackagefilepublishing.distribution = distrorelease.distribution AND
    potemplate.distrorelease = distrorelease.id AND
    sourcepackagefilepublishing.sourcepackagepublishing = sourcepackagepublishing.id AND
    sourcepackagefilepublishing.publishingstatus = 2 AND
    sourcepackagefilepublishing.distroreleasename = distrorelease.name AND
    sourcepackagefilepublishing.componentname = 'main' AND
    potemplate.languagepack IS FALSE;
*/

/* Give high priority to the packages that are part of language packs */
/*
UPDATE POTemplate
SET priority = 100
FROM sourcepackagefilepublishing, sourcepackagepublishing, distrorelease, sourcepackagename
WHERE
    sourcepackagefilepublishing.distribution = distrorelease.distribution AND
    potemplate.distrorelease = distrorelease.id AND
    sourcepackagefilepublishing.sourcepackagepublishing = sourcepackagepublishing.id AND
    sourcepackagefilepublishing.publishingstatus = 2 AND
    sourcepackagefilepublishing.distroreleasename = distrorelease.name AND
    sourcepackagefilepublishing.componentname = 'main' AND
    potemplate.languagepack IS TRUE;
*/

INSERT INTO LaunchpadDatabaseRevision VALUES (40, 54, 0);
