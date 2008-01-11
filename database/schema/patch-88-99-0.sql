SET client_min_messages=ERROR;

ALTER TABLE BugSubscription
ADD COLUMN subscribed_by integer NULL REFERENCES Person;

-- Make all existing subscriptions
-- subscribed_by the Launchpad Janitor
UPDATE BugSubscription
SET subscribed_by = 65
WHERE subscribed_by IS NULL;

ALTER TABLE BugSubscription
ALTER COLUMN subscribed_by SET NOT NULL;

INSERT INTO LaunchpadDatabaseRevision VALUES (88, 99, 0);
