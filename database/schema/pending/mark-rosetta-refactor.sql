
/* Allow the model to distinguish between translations that have been seen
 * recently and those that have been active recently. Also, allow us to have
 * translation suggestions that have never been active. */

SET client_min_messages=ERROR;

-- create the new columns
ALTER TABLE POTranslationSighting
    ADD COLUMN datelastseen timestamp without time zone;
ALTER TABLE POMsgSet
    ADD COLUMN fuzzyinlastrevision boolean;

-- for starters, we should set the datelastseen to the value of
-- datelastactive, since its the best guess we have
UPDATE POTranslationSighting SET datelastseen=datelastactive;

-- now we have values everywhere we can set a default and make it NOT NULL
ALTER TABLE POTranslationSighting ALTER COLUMN datelastseen
    SET DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'UTC');
ALTER TABLE POTranslationSighting ALTER COLUMN datelastseen
    SET NOT NULL;

-- from now on, we can't assume that every translation sighted has been
-- active
ALTER TABLE POTranslationSighting ALTER COLUMN datelastactive
    DROP NOT NULL;
ALTER TABLE POTranslationSighting ALTER COLUMN active
    SET DEFAULT False;

-- add sanity checking
ALTER TABLE POTranslationSighting ADD CONSTRAINT
potranslationsighting_pluralform_inlastrevision_key
UNIQUE (pluralform, pomsgset, NULLIF(inlastrevision, False));

ALTER TABLE POTranslationSighting ADD CONSTRAINT
potranslationsighting_pluralform_active_key
UNIQUE (pluralform, pomsgset, NULLIF(active, False));


