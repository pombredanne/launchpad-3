SET client_min_messages=ERROR;

-- Add the new field to know when was last updated a POTemplate.
ALTER TABLE POTemplate ADD COLUMN date_last_update timestamp without time zone;
-- This field is cached from other data in our database, we need to migrate it.
UPDATE POTemplate
SET date_last_update = (
    SELECT POMsgIDSighting.datefirstseen
    FROM POTMsgSet
         JOIN POMsgIDSighting ON POMsgIDSighting.inlastrevision = TRUE AND
                                 POMsgIDSighting.potmsgset=POTMsgset.id
    WHERE POTMsgSet.potemplate = POTemplate.id
    ORDER BY POMsgIDSighting.datefirstseen DESC
    LIMIT 1);

-- There are some POTemplates that don't have any message, this is usually due
-- broken files imported or that we just uploaded a file to create it and is
-- pending to be imported.
UPDATE POTemplate
SET date_last_update = (SELECT CURRENT_TIMESTAMP AT TIME ZONE 'UTC')
WHERE date_last_update IS NULL;

ALTER TABLE POTemplate ALTER COLUMN date_last_update SET DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'UTC');
ALTER TABLE POTemplate ALTER COLUMN date_last_update SET NOT NULL;

INSERT INTO LaunchpadDatabaseRevision VALUES (40, 99, 0);
