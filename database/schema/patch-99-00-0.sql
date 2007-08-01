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
SET date_incomplete = NOW()
WHERE bugtask.status = 15
AND date_incomplete IS NULL;

ALTER TABLE bugtask ADD CONSTRAINT bugtask_date_incomplete_recorded_chk
CHECK (status = 15 OR date_incomplete IS NULL);

INSERT INTO LaunchpadDatabaseRevision VALUES (99, 0, 0);