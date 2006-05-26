set client_min_messages=ERROR;

-- Create the potexport view to allow potemplate exports

CREATE OR REPLACE VIEW POTExport AS 
    SELECT (((COALESCE(potmsgset.id::text, 'X'::text) || '.'::text) ||
              COALESCE(pomsgidsighting.id::text, 'X'::text)) || '.'::text) AS id,
    potemplatename.name,
    potemplatename.translationdomain,
    potemplate.id AS potemplate,
    potemplate.productseries,
    potemplate.sourcepackagename,
    potemplate.distrorelease,
    potemplate.header,
    potemplate.languagepack,
    potmsgset.id AS potmsgset,
    potmsgset."sequence",
    potmsgset.commenttext,
    potmsgset.sourcecomment,
    potmsgset.flagscomment,
    potmsgset.filereferences,
    pomsgidsighting.pluralform,
    pomsgid.msgid
FROM pomsgid
    JOIN pomsgidsighting ON pomsgid.id = pomsgidsighting.pomsgid
    JOIN potmsgset ON potmsgset.id = pomsgidsighting.potmsgset
    JOIN potemplate ON potemplate.id = potmsgset.potemplate
    JOIN potemplatename ON potemplatename.id = potemplate.potemplatename;

INSERT INTO LaunchpadDatabaseRevision VALUES (40, 58, 0);

