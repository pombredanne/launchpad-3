/*
 * Changes to Rosetta tables for a more consistent names
 */

ALTER TABLE POMsgIDSighting RENAME firstseen TO datefirstseen;
ALTER TABLE POMsgIDSighting RENAME lastseen TO datelastseen;
ALTER TABLE POMsgIDSighting RENAME inpofile TO inslastrevision;

ALTER TABLE POTranslationSighting RENAME firstseen TO datefirstseen;
ALTER TABLE POTranslationSighting RENAME lasttouched TO datelastactive;
ALTER TABLE POTranslationSighting RENAME inpofile TO inlastrevision;
ALTER TABLE POTranslationSighting RENAME deprecated TO active;

/*
 * Changes to Malone tables to standardize names
 */
ALTER TABLE Bug RENAME nickname TO name;
ALTER TABLE Bug ADD COLUMN shortdesc text;
ALTER TABLE Bug ALTER COLUMN shortdesc SET NOT NULL;

/*
 * Fix typo in Rosetta tables
 */
ALTER TABLE Language RENAME COLUMN pluralexpresion TO pluralexpression;

