SET client_min_messages=ERROR;

-- Rename the answer-track-janitor to launchpad-janitor.
-- This system user will work in all areas of launchpad
UPDATE Person SET name='darshan-b' where name='janitor';

UPDATE Person SET
    displayname = 'Launchpad Janitor',
    name = 'janitor'
WHERE name = 'answer-tracker-janitor';

UPDATE emailaddress SET email = 'janitor@launchpad.net'
WHERE email = 'janitor@support.launchpad.net';

INSERT INTO LaunchpadDatabaseRevision VALUES (87, 48, 0);

