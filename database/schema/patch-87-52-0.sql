SET client_min_messages=ERROR;

DROP INDEX unique_entry_per_importer;

CREATE UNIQUE INDEX translationimportqueueentry__entry_per_importer__unq
ON TranslationImportQueueEntry (
                        importer,
                        path,
                        (COALESCE(potemplate, -1)),
                        (COALESCE(distrorelease, -1)),
                        (COALESCE(sourcepackagename, -1)),
                        (COALESCE(productseries, -1))
                        );

INSERT INTO LaunchpadDatabaseRevision VALUES (87, 52, 0);
