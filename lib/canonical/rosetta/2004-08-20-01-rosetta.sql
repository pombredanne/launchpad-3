/*
 * Changes to Rosetta tables for a more consistent names
 *
 * arch-tag: ae5200b0-6edf-47b6-a6d9-7e864e49695b
 */

ALTER TABLE POMsgIDSighting RENAME firstseen TO datefirstseen;
ALTER TABLE POMsgIDSighting RENAME lastseen TO datelastseen;
ALTER TABLE POMsgIDSighting RENAME inpofile TO inslastrevision;

ALTER TABLE POTranslationSighting RENAME firstseen TO datefirstseen;
ALTER TABLE POTranslationSighting RENAME lasttouched TO datelastactive;
ALTER TABLE POTranslationSighting RENAME inpofile TO inlastrevision;
ALTER TABLE POTranslationSighting RENAME deprecated TO active;
