SET client_min_messages TO error;

/*
 * Fixes for Malone bug watches
 */
ALTER TABLE BugSystem ADD COLUMN contactdetails text;

-- Add a serial id to ProjectBugSystem
ALTER TABLE ProjectBugSystem ADD COLUMN id integer;
SET client_min_messages TO fatal;
CREATE SEQUENCE projectbugsystem_id_seq;
SET client_min_messages TO error;
ALTER TABLE ProjectBugSystem ALTER COLUMN id SET NOT NULL;
ALTER TABLE ProjectBugSystem ALTER COLUMN id 
    SET DEFAULT nextval('projectbugsystem_id_seq');
-- And fix up the primary keys
ALTER TABLE ProjectBugSystem DROP CONSTRAINT projectbugsystem_pkey;
ALTER TABLE ProjectBugSystem ADD PRIMARY KEY (id);
ALTER TABLE ProjectBugSystem ADD UNIQUE (project, bugsystem);

-- BugSystem wants shortdesc, not description
ALTER TABLE BugSystem RENAME COLUMN description TO shortdesc;

-- Use owner consistantly
ALTER TABLE BugMessage RENAME COLUMN personmsg TO owner;

-- Make rfc822msgid required - these correspond to emails sent out
ALTER TABLE BugMessage ALTER COLUMN rfc822msgid SET NOT NULL;
ALTER TABLE BugMessage ADD UNIQUE(rfc822msgid);
