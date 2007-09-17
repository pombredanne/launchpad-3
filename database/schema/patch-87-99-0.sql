SET client_min_messages=ERROR;

ALTER TABLE bug
  ADD COLUMN date_last_message timestamp;

UPDATE bug
SET date_last_message = (
  SELECT max(message.datecreated)
  FROM bugmessage, message
  WHERE message.id = bugmessage.message
  AND bugmessage.bug = bug.id);

INSERT INTO LaunchpadDatabaseRevision VALUES (87, 99, 0);
