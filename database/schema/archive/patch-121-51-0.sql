SET client_min_messages=ERROR;

CREATE INDEX codeimportevent__message__date_created__idx
    ON CodeImportEvent(machine, date_created) WHERE machine IS NOT NULL;

INSERT INTO LaunchpadDatabaseRevision VALUES (121, 51, 0);
