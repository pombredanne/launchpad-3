SET client_min_messages=ERROR;

-- Backport indexes added to production for Rosetta data cleanup
CREATE INDEX pofiletranslator__latest_message__idx
ON POFileTranslator(latest_message);

CREATE INDEX translationmessage__pofile__submitter__idx
ON TranslationMessage(pofile, submitter);

INSERT INTO LaunchpadDatabaseRevision VALUES (88, 42, 1);

