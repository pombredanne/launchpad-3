SET client_min_messages=ERROR;

/* This patch defines two tables which together fill the role of the
   soon to-be-merged Build and BuildQueue tables in Soyuz:

    - CodeImportJob (CIJC) -- queued and running jobs
    - codeimportresult (CIJP) -- completed (or killed) jobs

   There is another patch (patch-87-93-0.sql) that just defines a CodeImportJob
   table.

   There are arguments pro and con for separating CIJC and CIJP.

     * Pro: Makes the dba's life a little bit easier
     * Pro: CIJP can be append-only and CIJC must be CRUD.
     * Pro: Separates two things that are conceptually separate: the reasons for
            accessing current jobs are different from examing past jobs.  Current
            plan calls for each active code import to always have a running or 
            pending job, which is easier to understand with a table for running
            or pending jobs.
     * Con: Two tables that have some columns in common.
     * Con: Makes the developers life a bit harder
     * Con: CIJP is not going to be really CR, to support CodeImport deletion.

   It is assumed with appropriate indexes, performance will be a non-issue in
   this decision.
*/

CREATE TABLE CodeImportJob (
    id SERIAL PRIMARY KEY,
    date_created TIMESTAMP WITHOUT TIME ZONE
        DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'UTC') NOT NULL,
    code_import integer NOT NULL
        CONSTRAINT codeimportjob__code_import__key UNIQUE
        CONSTRAINT codeimportjob__code_import__fk REFERENCES CodeImport,
    machine integer
        CONSTRAINT codeimportjob__machine__fk REFERENCES CodeImportMachine,
    date_due TIMESTAMP WITHOUT TIME ZONE NOT NULL,
    state integer NOT NULL, -- one of PENDING (10), SCHEDULED (20), RUNNING (30)
    -- reason inferred from requesting_user. Add back later
    -- if we need more reasons.
    -- reason integer NOT NULL, -- one of REQUEST (100), INTERVAL (200)
    requesting_user integer
        CONSTRAINT codeimportjob__requesting_user__fk REFERENCES Person,
    ordering integer,
    heartbeat TIMESTAMP WITHOUT TIME ZONE,
    logtail text,
    date_started TIMESTAMP WITHOUT TIME ZONE,
    
    CONSTRAINT valid_state CHECK (CASE 
        WHEN state = 10 THEN -- PENDING
            machine IS NULL
            AND ordering IS NULL
            AND heartbeat IS NULL
            AND date_started IS NULL
            AND logtail IS NULL
        WHEN state = 20 THEN -- SCHEDULED
            machine IS NOT NULL
            AND ordering IS NOT NULL
            AND heartbeat IS NULL
            AND date_started IS NULL
            AND logtail IS NULL
        WHEN state = 30 THEN -- RUNNING
            machine IS NOT NULL
            AND ordering IS NULL
            AND heartbeat IS NOT NULL
            AND date_started IS NOT NULL
            AND logtail IS NOT NULL
        ELSE
            FALSE
        END)
    );

/* Retrieval of current jobs by code import. */

CREATE INDEX codeimportjob__code_import__date_created__idx
  ON CodeImportJob(code_import, date_created);

/* Retrieval of current jobs by machine. */

CREATE INDEX codeimportjob__machine__date_created__idx
  ON CodeImportJob(machine, date_created);

-- Keep people merge happy
CREATE INDEX codeimportjob__requesting_user__idx
  ON CodeImportJob(requesting_user);

CREATE TABLE CodeImportResult (
    id SERIAL PRIMARY KEY,
    date_created TIMESTAMP WITHOUT TIME ZONE
        DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'UTC') NOT NULL,
    code_import integer
        CONSTRAINT codeimportresult__code_import__fk REFERENCES CodeImport
        ON DELETE CASCADE,
    machine integer
        CONSTRAINT codeimportresult__machine__fk REFERENCES CodeImportMachine,
    requesting_user integer
        CONSTRAINT codeimportresult__requesting_user__fk REFERENCES Person,
    log_excerpt text,
    log_file integer
        CONSTRAINT codeimportresult__log_file__fk REFERENCES LibraryFileAlias,
    status integer NOT NULL, -- SUCCESS, FAILURE, CHECKOUT_FAILURE, KILLED, etc
    date_started TIMESTAMP WITHOUT TIME ZONE
    );

-- Keep people merge happy
CREATE INDEX codeimportresult__requesting_user__idx
  ON CodeImportResult(requesting_user);

/* Retrieval of past jobs by code import. */

CREATE INDEX codeimportresult__code_import__date_created__idx
  ON CodeImportResult(code_import, date_created);

/* Retrieval of past jobs by machine. */

CREATE INDEX codeimportresult__machine__date_created__idx
  ON CodeImportResult(machine, date_created);

/* Code import audit trail */

CREATE TABLE CodeImportEvent (
    id SERIAL PRIMARY KEY,
    date_created TIMESTAMP WITHOUT TIME ZONE
        DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'UTC') NOT NULL,

    entry_type integer NOT NULL,
    code_import integer
        CONSTRAINT codeimportevent__code_import__fk REFERENCES CodeImport
        ON DELETE CASCADE,
    -- Already stored in the codeimportresult.
    -- log_file integer REFERENCES LibraryFileAlias,
    person integer
        CONSTRAINT codeimportevent__person__fk REFERENCES Person,
    machine integer
        CONSTRAINT codeimportevent__machine__fk REFERENCES CodeImportMachine
    );

-- Make people merge happy
CREATE INDEX codeimportevent__person__idx
    ON CodeImportEvent(person) WHERE person IS NOT NULL;

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
    event INTEGER
        CONSTRAINT codeimporteventdata__event__fk REFERENCES CodeImportEvent
        ON DELETE CASCADE,
    data_type integer NOT NULL,
    data_value text,
    CONSTRAINT codeimporteventdata__event__data_type__key
        UNIQUE (event, data_type)
    );

/*
    Update: Maintaining the event table using triggers doesn't gain us
    anything, as instead of code needing to make updates through defined
    APIs code instead needs to remember to update all these extra columns
    that are required for the approach to log the required information.
    It also greatly reduces our flexibility, where if we need to change
    what is being logged we need to wait an entire cycle for the next thaw
    and release to happen, and might need to add yet further columns to
    tables detailing information we want logged making the data model nastier.
    Add to this the general crappiness of maintaining code in stored
    procedures, made even more complex in that this code will be run by both
    production and edge environments, and it really seems best to maintain
    the event table at the application level.

   The plan is to create the event journal from within database triggers.
   This means that all the information that we want to get into the event
   journal must be present in the content objects so the triggers can get at
   them. 

ALTER TABLE CodeImport ADD COLUMN modified_by integer
    CONSTRAINT codeimport__modified_by__fk REFERENCES Person;
ALTER TABLE CodeImportMachine ADD COLUMN quiescing_requested_by integer
    CONSTRAINT codeimportmachine__quiescing_requested_by__fk REFERENCES Person;
ALTER TABLE CodeImportMachine ADD COLUMN quiescing_message text;
ALTER TABLE CodeImportMachine ADD COLUMN offline_reason integer;
ALTER TABLE CodeImportResult ADD COLUMN killing_user integer
    CONSTRAINT codeimportresult__killing_user__fk REFERENCES Person;

ALTER TABLE CodeImportResult ADD CONSTRAINT valid_killing_user CHECK (CASE
    WHEN status = 320 THEN -- KILLED
        killing_user IS NOT NULL
    ELSE
        killing_user IS NULL
    END);

-- The obligatory people-merge indices
CREATE INDEX codeimportmachine__quiescing_requested_by__idx
    ON CodeImportMachine(quiescing_requested_by)
    WHERE quiescing_request_by IS NOT NULL;
CREATE INDEX codeimportresult__killing_user__idx
    ON CodeImportResult(killing_user)
    WHERE killing_user IS NOT NULL;
*/

ALTER TABLE codeimportmachine_hostname_key
    RENAME TO codeimportmachine__hostname__key;

INSERT INTO LaunchpadDatabaseRevision VALUES(87, 50, 0);
