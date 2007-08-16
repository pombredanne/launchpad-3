SET client_min_messages=ERROR;

/* This patch defines two tables which together fill the role of the
   soon to-be-merged Build and BuildQueue tables in Soyuz:

    - CodeImportJobCurrent (CIJC) -- queued and running jobs
    - CodeImportJobPast (CIJP) -- completed (or killed) jobs

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

CREATE TABLE CodeImportJobCurrent (
    id SERIAL PRIMARY KEY,
    date_created TIMESTAMP WITHOUT TIME ZONE
        DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'UTC') NOT NULL,
    code_import INT NOT NULL UNIQUE REFERENCES CodeImport,
    machine INT REFERENCES CodeImportMachine,
    date_due TIMESTAMP WITHOUT TIME ZONE NOT NULL,
    state INT NOT NULL, -- one of PENDING (10), SCHEDULED (20), RUNNING (30)
    reason INT NOT NULL, -- one of REQUEST (100), INTERVAL (200)
    requesting_user INT REFERENCES Person,
    ordering INT,
    heartbeat TIMESTAMP WITHOUT TIME ZONE,
    logtail VARCHAR,
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
        END),

    CONSTRAINT requesting_user_is_set CHECK (CASE
        WHEN reason = 100 THEN -- REQUEST
            requesting_user IS NOT NULL
        WHEN reason = 200 THEN -- INTERVAL
            requesting_user IS NULL
        ELSE
            FALSE
        END)
    );

/* Retrieval of current jobs by code import. */

CREATE INDEX codeimportjobcurrent__code_import__date_created__idx
  ON CodeImportJobCurrent(code_import, date_created);

/* Retrieval of current jobs by machine. */

CREATE INDEX codeimportjobcurrent__machine__date_created__idx
  ON CodeImportJobCurrent(machine, date_created);

-- Keep people merge happy
CREATE INDEX codeimportjobcurrent__requesting_user__idx
  ON CodeImportJobCurrent(requesting_user);

CREATE TABLE CodeImportJobPast (
    id SERIAL PRIMARY KEY,
    date_created TIMESTAMP WITHOUT TIME ZONE
        DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'UTC') NOT NULL,
    code_import INT REFERENCES CodeImport,
    machine integer REFERENCES CodeImportMachine,
    log_excerpt VARCHAR,
    log_file INT REFERENCES LibraryFileAlias,
    status INT NOT NULL, -- SUCCESS, FAILURE, CHECKOUT_FAILURE, KILLED, etc
    date_started TIMESTAMP WITHOUT TIME ZONE
    );

/* Retrieval of past jobs by code import. */

CREATE INDEX codeimportjobpast__code_import__date_created__idx
  ON CodeImportJobPast(code_import, date_created);

/* Retrieval of past jobs by machine. */

CREATE INDEX codeimportjobpast__machine__date_created__idx
  ON CodeimportJobPast(machine, date_created);

INSERT INTO LaunchpadDatabaseRevision VALUES(87, 87, 0);
