set client_min_messages=ERROR;

/* Restructure the cve system to be a proper CVE tracker. Essentially we
 * want to treat CVE entries as first class citizens. */

CREATE TABLE CVE (
  id                 serial PRIMARY KEY,
  sequence           text NOT NULL CONSTRAINT valid_cve_ref
                                   CHECK (valid_cve(sequence)),
  status             integer NOT NULL,
  description        text NOT NULL,
  datecreated        timestamp WITHOUT TIME ZONE NOT NULL DEFAULT
                               (CURRENT_TIMESTAMP AT TIME ZONE 'UTC'),
  datemodified       timestamp WITHOUT TIME ZONE NOT NULL DEFAULT
                               (CURRENT_TIMESTAMP AT TIME ZONE 'UTC')
);

INSERT INTO CVE (sequence, status, description) 
  SELECT cveref, cvestate, title FROM CVERef;

ALTER TABLE CVE ADD CONSTRAINT cve_sequence_uniq UNIQUE (sequence);

CREATE INDEX cve_datecreated_idx ON CVE(datecreated);

CREATE INDEX cve_datemodified_idx ON CVE(datemodified);

CREATE TABLE BugCve (
  id                 serial PRIMARY KEY,
  bug                integer NOT NULL CONSTRAINT bugcve_bug_fk
                             REFERENCES Bug(id),
  cve                integer NOT NULL CONSTRAINT bugcve_cve_fk
                             REFERENCES CVE(id)
);

INSERT INTO BugCve (bug, cve)
    SELECT CveRef.bug, CVE.id FROM CveRef INNER JOIN CVE ON
        CveRef.cveref = CVE.sequence;

ALTER TABLE BugCve ADD CONSTRAINT bugcve_bug_cve_uniq UNIQUE (bug, cve);

CREATE INDEX bugcve_cve_index ON BugCve(cve);

/* CVE References
   This is somewhat confusing, since we used to have a CVERef table, which
   was a bug-cve combo, but with the new structure we also want to record
   the information that the CVE group publishes about OTHER sites referring
   to this CVE issue.
*/

CREATE TABLE CveReference (
  id              serial PRIMARY KEY,
  cve             integer NOT NULL CONSTRAINT cvereference_cve_fk
                                   REFERENCES CVE(id),
  source          text NOT NULL,
  content         text NOT NULL,
  url             text
);

CREATE INDEX cvereference_cve_idx ON CveReference(cve);

/* park the old cveref table */

ALTER TABLE CVERef RENAME TO CveRefObsolete;

INSERT INTO LaunchpadDatabaseRevision VALUES (25,25,0);

