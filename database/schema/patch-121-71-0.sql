SET client_min_messages=ERROR;

/*
Drop foreign key constraints between EmailAddress and Person, and between
Person and Account, and between MailingListSubscription and EmailAddress.
We cannot have foreign key constraints across replication
sets, and code will just have to cope if it tries to access a row that
no longer exists or has not yet been replicated.
*/

ALTER TABLE MailingListSubscription
    DROP CONSTRAINT mailinglistsubscription__person__email_address__fk;

ALTER TABLE EmailAddress
    DROP CONSTRAINT emailaddress__account__person__fk,
    DROP CONSTRAINT emailaddress_person_fk,
    DROP CONSTRAINT emailaddress__person__id__key;

CREATE INDEX emailaddress__person__status__idx ON EmailAddress(person, status);
DROP INDEX emailaddress_person_status_idx;

DROP INDEX person_name_key;
ALTER TABLE Person
    DROP CONSTRAINT person_account_fkey,
    DROP CONSTRAINT person__account__id__key,
    ADD CONSTRAINT person__account__key UNIQUE (account),
    ADD CONSTRAINT person__name__key UNIQUE (name);

INSERT INTO LaunchpadDatabaseRevision VALUES (121, 71, 0);

