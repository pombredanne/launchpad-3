SET client_min_messages=ERROR;

CREATE TABLE BugNotificationRecipient (
  id serial PRIMARY KEY,
  bug_notification INT NOT NULL REFERENCES BugNotification(id),
  person INT NOT NULL REFERENCES Person(id),
  reason_header TEXT NOT NULL,
  reason_body TEXT NOT NULL,
  CONSTRAINT bugnotificationrecipient__bug_notificaion__person__key
        UNIQUE (bug_notification, person)
);

INSERT INTO LaunchpadDatabaseRevision VALUES (121, 24, 0);
