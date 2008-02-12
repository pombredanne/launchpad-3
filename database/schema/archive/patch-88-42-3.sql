SET client_min_messages=ERROR;

CREATE INDEX translationimportqueueentry__context__path__idx
    ON TranslationImportQueueEntry(
        distroseries, sourcepackagename, productseries, path);

INSERT INTO LaunchpadDatabaseRevision VALUES (88, 42, 3);

