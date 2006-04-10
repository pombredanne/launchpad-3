SET client_min_messages=ERROR;

-- This constraint is nearly useless, as it can only prevent exact matches
-- rather than similar titles.
ALTER TABLE PollOption DROP CONSTRAINT polloption_shortname_key;

-- Improve displayname constraints somewhat
ALTER TABLE Person ADD CONSTRAINT non_empty_displayname
    CHECK (trim(displayname) <> '');

INSERT INTO LaunchpadDatabaseRevision VALUES (40, 45, 0);

