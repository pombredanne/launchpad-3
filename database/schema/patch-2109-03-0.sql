-- Copyright 2009 Canonical Ltd.  This software is licensed under the
-- GNU Affero General Public License version 3 (see the file LICENSE).

SET client_min_messages=ERROR;

CREATE TABLE BugNotificationAttachment (
    id serial PRIMARY KEY,
    message INTEGER NOT NULL REFERENCES Message(id),
    bug_notification INTEGER NOT NULL REFERENCES BugNotification(id)
);

CREATE INDEX bugnotificationattachment__bug_notification__idx
    ON BugNotificationAttachment (bug_notification);

CREATE INDEX bugnotificationattachment__message__idx
    ON BugNotificationAttachment(message);

INSERT INTO LaunchpadDatabaseRevision VALUES (2109, 3, 0);
