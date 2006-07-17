SET client_min_messages=ERROR;

ALTER TABLE Bug ADD COLUMN date_last_updated timestamp without time zone;

UPDATE Bug SET date_last_updated=max_date_changed
FROM (
    SELECT BugActivity.bug, max(datechanged) as max_date_changed
    FROM BugActivity GROUP BY bug
    ) AS Activity
WHERE Bug.id = Activity.bug AND date_last_updated IS NULL;

UPDATE Bug SET date_last_updated=datecreated
WHERE date_last_updated IS NULL;

ALTER TABLE Bug ALTER COLUMN date_last_updated SET DEFAULT
CURRENT_TIMESTAMP AT TIME ZONE 'UTC';
ALTER TABLE Bug ALTER COLUMN date_last_updated SET NOT NULL;

CREATE INDEX bug__datecreated__idx ON Bug(datecreated);
CREATE INDEX bug__date_last_updated__idx ON Bug(date_last_updated);

-- Rename a badly named index that slipped through
DROP INDEX foo;
CREATE UNIQUE INDEX supportcontact__distribution__person__key
    ON SupportContact(distribution, person)
    WHERE sourcepackagename IS NULL;

INSERT INTO LaunchpadDatabaseRevision VALUES (40, 52, 0);
