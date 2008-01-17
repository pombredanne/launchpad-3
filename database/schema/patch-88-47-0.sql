SET client_min_messages=ERROR;

ALTER TABLE BugSubscription
ADD COLUMN subscribed_by integer NULL REFERENCES Person;

UPDATE BugSubscription
SET subscribed_by = person
WHERE subscribed_by IS NULL;

ALTER TABLE BugSubscription ALTER COLUMN subscribed_by SET NOT NULL;

-- Index needed for people merge
CREATE INDEX bugsubscription__subscribed_by__idx
ON BugSubscription(subscribed_by);

INSERT INTO LaunchpadDatabaseRevision VALUES (88, 47, 0);
