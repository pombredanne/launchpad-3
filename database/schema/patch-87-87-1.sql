SET client_min_messages=ERROR;

CREATE TABLE CodeImportEvent (
    id SERIAL PRIMARY KEY,
    date_created TIMESTAMP WITHOUT TIME ZONE
        DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'UTC') NOT NULL,

    entry_type integer NOT NULL,
    code_import integer REFERENCES CodeImport,
    log_file INTEGER REFERENCES LibraryFileAlias,
    person integer REFERENCES Person,
    machine integer REFERENCES CodeImportMachine
    );

/* Index used to display events time-sorted. Since several events
   can be created in the same transaction, id is needed to disambiguate
   date_created. */

CREATE INDEX codeimportevent__date_created__id__idx
    ON CodeImportEvent(date_created, id);

/* Index used to display events for a specific CodeImport. Similar to
   previous one. */

CREATE INDEX codeimportevent__code_import__date_created__id__idx
    ON CodeImportEvent(code_import, date_created, id);

CREATE TABLE CodeImportEventData (
    id SERIAL PRIMARY KEY,
    event INTEGER REFERENCES CodeImportEvent,
    data_type INT NOT NULL,
    data_value VARCHAR
    );

CREATE UNIQUE INDEX codeimporteventdata__event__data_type__unique_idx
    ON CodeImportEventData(event, data_type);

/* The plan is to create the event journal from within database triggers.
   This means that all the information that we want to get into the event
   journal must be present in the content objects so the triggers can get at
   them. */

ALTER TABLE CodeImport ADD COLUMN modified_by INT REFERENCES Person;
ALTER TABLE CodeImportMachine ADD COLUMN quiescing_requested_by INT REFERENCES Person;
ALTER TABLE CodeImportMachine ADD COLUMN quiescing_message VARCHAR;
ALTER TABLE CodeImportMachine ADD COLUMN offline_reason INT;
ALTER TABLE CodeImportJobPast ADD COLUMN killing_user INT REFERENCES Person;

ALTER TABLE CodeImportJobPast ADD CONSTRAINT valid_killing_user CHECK (CASE
    WHEN status = 320 THEN -- KILLED
        killing_user IS NOT NULL
    ELSE
        killing_user IS NULL
    END);

/* The obligatory people-merge indices */
CREATE INDEX codeimportevent__person__idx
    ON CodeImportEvent(person);
CREATE INDEX codeimportmachine__quiescing_requested_by__idx
    ON CodeImportMachine(quiescing_requested_by);
CREATE INDEX codeimportjobpast__killing_user__idx
    ON CodeImportJobPast(killing_user);

INSERT INTO LaunchpadDatabaseRevision VALUES(87, 87, 1);
