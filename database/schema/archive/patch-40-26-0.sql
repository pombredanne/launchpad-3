SET client_min_messages=ERROR;

-- Rename the 'buttsource' Person to 'vcs-imports'.
UPDATE Person
SET name = 'vcs-imports', 
    teamdescription = 'Owner of branches imported from non-bzr VCS',
    displayname = 'VCS imports'
WHERE name = 'buttsource';

INSERT INTO LaunchpadDatabaseRevision VALUES (40, 26, 0);
