SET client_min_messages=ERROR;

CREATE TABLE BugNotificationRecipient (
  id serial NOT NULL,
  bugnotification INT NOT NULL REFERENCES BugNotification(id),
  person INT NOT NULL REFERENCES Person(id),
  rationale TEXT NOT NULL,
  reason TEXT NOT NULL,
  CONSTRAINT bug_notificaion_recipient_one_rationale
    UNIQUE (bugnotification, person)
);

INSERT INTO LaunchpadDatabaseRevision VALUES (121, 99, 0);
