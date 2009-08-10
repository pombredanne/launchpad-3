SET client_min_messages=ERROR;

ALTER TABLE BugNotificationRecipient
    DROP CONSTRAINT bugnotificationrecipient_bug_notification_fkey,
    ADD CONSTRAINT bugnotificationrecipient__bug_notification__fk
        FOREIGN KEY (bug_notification) REFERENCES BugNotification
            ON DELETE CASCADE;

INSERT INTO LaunchpadDatabaseRevision VALUES (2207, 2, 0);
