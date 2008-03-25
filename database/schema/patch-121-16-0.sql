SET client_min_messages=ERROR;

ALTER TABLE MailingList RENAME welcome_message_text TO welcome_message;

ALTER TABLE MailingListBan RENAME reason_text TO reason;

ALTER TABLE Person
    RENAME personal_standing_reason_text TO personal_standing_reason;

INSERT INTO LaunchpadDatabaseRevision VALUES (121, 16, 0);

