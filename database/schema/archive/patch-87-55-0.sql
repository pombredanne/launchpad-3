SET client_min_messages=ERROR;

ALTER TABLE bug
  ADD COLUMN date_last_message timestamp without time zone;

CREATE INDEX bug__date_last_message__idx ON bug (date_last_message);

UPDATE Bug SET date_last_message = max_date_created
FROM (
    SELECT BugMessage.bug, max(message.datecreated) AS max_date_created
    FROM BugMessage, Message
    WHERE Message.id = BugMessage.message
    GROUP BY BugMessage.bug
    ) AS MessageSummary
WHERE Bug.id = MessageSummary.bug;

CREATE TRIGGER set_date_last_message_t
AFTER INSERT OR UPDATE OR DELETE ON BugMessage
FOR EACH ROW EXECUTE PROCEDURE set_bug_date_last_message();

INSERT INTO LaunchpadDatabaseRevision VALUES (87, 55, 0);

