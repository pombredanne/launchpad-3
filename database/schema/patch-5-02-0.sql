SET client_min_messages=ERROR;

/*

 I've changed my mind about the CVE data storage, so here's a patch
 to restructure the BugExternalRef stuff to create a separate table
 for CVE data.

*/

-- Create the CVERef table
CREATE TABLE CVERef (
  id           serial PRIMARY KEY,
  bug          integer NOT NULL REFERENCES Bug,
  cveref       text NOT NULL,
  title        text NOT NULL,
  datecreated  timestamp without time zone
      DEFAULT (current_timestamp AT TIME ZONE 'UTC'),
  owner        integer NOT NULL REFERENCES Person
);


-- Populate it with existing data from the BugExternalRef table
INSERT INTO CVERef ( bug, cveref, title, datecreated, owner ) SELECT
                   bug, data, description, datecreated, owner FROM
		   BugExternalRef WHERE BugExternalRef.bugreftype = 1;

-- Remove the CVE refs from the BugExternalRef table now we have them
-- in the CVERef table
DELETE FROM BugExternalRef WHERE bugreftype = 1;

-- Get rid of the bugreftype column from BugExternalRef
ALTER TABLE BugExternalRef DROP COLUMN BugRefType;
ALTER TABLE BugExternalRef RENAME COLUMN data TO url;
ALTER TABLE BugExternalRef RENAME COLUMN description TO title;

UPDATE LaunchpadDatabaseRevision SET major=5, minor=2, patch=0;

