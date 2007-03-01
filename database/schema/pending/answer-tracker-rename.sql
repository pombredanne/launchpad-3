BEGIN;

-- Rename the janitor.

UPDATE Person SET name = 'answer-tracker-janitor',
    displayname = 'Launchpad Answer Tracker Janitor'
    WHERE name = 'support-tracker-janitor';

COMMIT;

