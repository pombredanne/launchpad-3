SET client_min_messages=ERROR;

ALTER TABLE EmailAddress ADD CONSTRAINT valid_account_for_person
    CHECK (check_email_address_person_account(person, account));
ALTER TABLE Person ADD CONSTRAINT valid_account_for_emailaddresses
    CHECK (check_person_email_address_account(id, account));

INSERT INTO LaunchpadDatabaseRevision VALUES (2208, 99, 0);
