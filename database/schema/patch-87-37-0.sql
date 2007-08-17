SET client_min_messages=ERROR;

/* BugTaskStatus.INCOMPLETE == 15 */

ALTER TABLE bugtask
ADD COLUMN date_incomplete timestamp without time zone;

UPDATE bugtask
SET date_incomplete = (
 SELECT bugactivity.datechanged as date_incomplete
 FROM bugactivity
 WHERE bugactivity.bug = bugtask.bug
 AND bugactivity.whatchanged LIKE '%: status'
 ORDER BY date_incomplete DESC
 LIMIT 1)
WHERE bugtask.status = 15;

UPDATE bugtask
SET date_incomplete = CURRENT_TIMESTAMP AT TIME ZONE 'UTC'
WHERE bugtask.status = 15
AND date_incomplete IS NULL;

CREATE INDEX bugtask__date_incomplete__idx ON BugTask(date_incomplete)
   WHERE date_incomplete IS NOT NULL;

INSERT INTO LaunchpadDatabaseRevision VALUES (87, 37, 0);
