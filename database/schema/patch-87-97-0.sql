SET client_min_messages=ERROR;

-- Rename the answer-track-janitor to launchpad-janitor.
-- This system user will work in all areas of launchpad
UPDATE Person
SET 
    displayname = 'Launchpad Janitor',
    name = 'launchpad-janitor',
    openid_identifier = 'launchpad-janitor_oid'
WHERE 
    name = 'answer-tracker-janitor';

UPDATE emailaddress
SET
    email = 'janitor@launchpad.net'
WHERE 
    email = 'janitor@support.launchpad.net';

-- Rename answertracker to launchpadjanitor and remove the
-- unused teammembership role.
-- I do not want to go into any detail regarding how bitter
-- I am that I had to write a function to safely migrate the
-- database janitor roles.
-- select rename_janitor_roles();

INSERT INTO LaunchpadDatabaseRevision VALUES (87, 97, 0);

