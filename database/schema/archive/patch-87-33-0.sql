-- Add message context to the POTMsgSets, used to disambiguate
-- message sets with identical msgid's but with possible different
-- translations

SET client_min_messages=ERROR;

ALTER TABLE POTMsgSet ADD COLUMN context text DEFAULT NULL;

DROP INDEX potmsgset__potemplate__primemsgid__key;

CREATE UNIQUE INDEX potmsgset__potemplate__context__primemsgid__key ON potmsgset USING btree (potemplate, context, primemsgid) WHERE context IS NOT NULL;

CREATE UNIQUE INDEX potmsgset__potemplate__no_context__primemsgid__key ON potmsgset USING btree (potemplate, primemsgid) WHERE context IS NULL;

DROP VIEW poexport;

CREATE VIEW poexport AS
    SELECT ((((((COALESCE((potmsgset.id)::text, 'X'::text) || '.'::text) || COALESCE((pomsgset.id)::text, 'X'::text)) || '.'::text) || COALESCE((pomsgidsighting.id)::text, 'X'::text)) || '.'::text) || COALESCE((posubmission.id)::text, 'X'::text)) AS id, potemplatename.name, potemplatename.translationdomain, potemplate.id AS potemplate, potemplate.productseries, potemplate.sourcepackagename, potemplate.distrorelease, potemplate."header" AS potheader, potemplate.languagepack, pofile.id AS pofile, pofile."language", pofile.variant, pofile.topcomment AS potopcomment, pofile."header" AS poheader, pofile.fuzzyheader AS pofuzzyheader, potmsgset.id AS potmsgset, potmsgset."sequence" AS potsequence, potmsgset.commenttext AS potcommenttext, potmsgset.sourcecomment, potmsgset.flagscomment, potmsgset.filereferences, pomsgset.id AS pomsgset, pomsgset."sequence" AS posequence, pomsgset.iscomplete, pomsgset.obsolete, pomsgset.isfuzzy, pomsgset.commenttext AS pocommenttext, pomsgidsighting.pluralform AS msgidpluralform, posubmission.pluralform AS translationpluralform, posubmission.id AS activesubmission, potmsgset.context, pomsgid.msgid, potranslation.translation FROM ((((((((pomsgid JOIN pomsgidsighting ON ((pomsgid.id = pomsgidsighting.pomsgid))) JOIN potmsgset ON ((potmsgset.id = pomsgidsighting.potmsgset))) JOIN potemplate ON ((potemplate.id = potmsgset.potemplate))) JOIN potemplatename ON ((potemplatename.id = potemplate.potemplatename))) JOIN pofile ON ((potemplate.id = pofile.potemplate))) LEFT JOIN pomsgset ON (((potmsgset.id = pomsgset.potmsgset) AND (pomsgset.pofile = pofile.id)))) LEFT JOIN posubmission ON (((pomsgset.id = posubmission.pomsgset) AND posubmission.active))) LEFT JOIN potranslation ON ((potranslation.id = posubmission.potranslation)));

DROP VIEW potexport;

CREATE VIEW potexport AS
    SELECT (((COALESCE((potmsgset.id)::text, 'X'::text) || '.'::text) || COALESCE((pomsgidsighting.id)::text, 'X'::text)) || '.'::text) AS id, potemplatename.name, potemplatename.translationdomain, potemplate.id AS potemplate, potemplate.productseries, potemplate.sourcepackagename, potemplate.distrorelease, potemplate."header", potemplate.languagepack, potmsgset.id AS potmsgset, potmsgset."sequence", potmsgset.commenttext, potmsgset.sourcecomment, potmsgset.flagscomment, potmsgset.filereferences, pomsgidsighting.pluralform, potmsgset.context, pomsgid.msgid FROM ((((pomsgid JOIN pomsgidsighting ON ((pomsgid.id = pomsgidsighting.pomsgid))) JOIN potmsgset ON ((potmsgset.id = pomsgidsighting.potmsgset))) JOIN potemplate ON ((potemplate.id = potmsgset.potemplate))) JOIN potemplatename ON ((potemplatename.id = potemplate.potemplatename)));

INSERT INTO LaunchpadDatabaseRevision VALUES (87, 33, 0);

