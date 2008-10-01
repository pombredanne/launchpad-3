SET client_min_messages=ERROR;

CREATE TABLE BugNotificationAttachment (
    id serial PRIMARY KEY,
    message INTEGER NOT NULL REFERENCES Message(id),
    bug_notification INTEGER NOT NULL REFERENCES BugNotification(id)
);

CREATE INDEX bugnotificationattachment__bug_notification__idx
    ON BugNotificationAttachment (bug_notification);

INSERT INTO LaunchpadDatabaseRevision VALUES (121, 99, 0);
