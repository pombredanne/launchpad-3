SET client_min_messages=ERROR;

-- Backup historical data until we can deal with it per Bug #407288.
-- We keep the person foreign key constraint so this data is modified
-- by Person merges.
CREATE TABLE BugNotificationRecipientArchive AS
    SELECT * FROM BugNotificationRecipient;
CREATE INDEX bugnotificationrecipientarchive__person__idx
    ON bugnotificationrecipientarchive(person);
ALTER TABLE bugnotificationrecipientarchive 
    ADD CONSTRAINT bugnotificationrecipientarchive_pk PRIMARY KEY (id),
    ADD CONSTRAINT bugnotificationrecipientarchive__person__fk
        FOREIGN KEY (person) REFERENCES Person;

INSERT INTO LaunchpadDatabaseRevision VALUES (2207, 2, 0);

