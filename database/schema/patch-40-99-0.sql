SET client_min_messages=ERROR;

-- First, rename severity to importance, to avoid leaky abtractions
-- and to ensure we update all the callsites to reflect the new values.
ALTER TABLE BugTask RENAME COLUMN severity TO importance;

-- Then, set the default to the new value 'Untriaged'.
ALTER TABLE BugTask ALTER COLUMN importance SET DEFAULT 5;
  
INSERT INTO LaunchpadDatabaseRevision VALUES (40, 99, 0);
