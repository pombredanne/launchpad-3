
SET client_min_messages=ERROR;

/* Get rid of the BugTrackerType table, in favour of a dbschema entry. */

ALTER TABLE BugTracker DROP CONSTRAINT bugtracker_bugtrackerttype_fk;

DROP TABLE BugTrackerType;

ALTER TABLE CVERef ADD COLUMN cvestate integer;

UPDATE CVERef SET cveref=substring(cveref from 5), cvestate=1
    WHERE cveref LIKE 'CAN-%';
UPDATE CVERef SET cveref=substring(cveref from 5), cvestate=2
    WHERE cveref LIKE 'CVE-%';

ALTER TABLE CVERef ALTER COLUMN cvestate SET DEFAULT 1;
ALTER TABLE CVERef ALTER COLUMN cvestate SET NOT NULL;

INSERT INTO LaunchpadDatabaseRevision VALUES (17, 39, 0);
