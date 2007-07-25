SET client_min_messages=ERROR;

-- No point adding this yet, as this column is not being maintained
-- properly until salgado's bug-2773 branch lands.
-- UPDATE Person SET account_status = 10 WHERE account_status IS NULL;
-- ALTER TABLE Person ALTER COLUMN account_status SET DEFAULT 10;
-- ALTER TABLE Person ALTER COLUMN account_status SET NOT NULL;

ALTER TABLE Person
ALTER COLUMN personal_standing SET DEFAULT 0,
ALTER COLUMN mailing_list_receive_duplicates SET DEFAULT TRUE,
ALTER COLUMN mailing_list_auto_subscribe_policy SET DEFAULT 1;

UPDATE Person SET
    personal_standing = DEFAULT,
    mailing_list_receive_duplicates = DEFAULT,
    mailing_list_auto_subscribe_policy = DEFAULT
WHERE
    personal_standing IS NULL
    AND mailing_list_receive_duplicates IS NULL
    AND mailing_list_auto_subscribe_policy IS NULL;

ALTER TABLE Person
ALTER COLUMN personal_standing SET NOT NULL,
ALTER COLUMN mailing_list_receive_duplicates SET NOT NULL,
ALTER COLUMN mailing_list_auto_subscribe_policy SET NOT NULL,
-- Populated by trigger
ALTER COLUMN openid_identifier SET NOT NULL;

-- Too slow - do during downtime
-- ALTER TABLE POMsgSet ALTER COLUMN language SET NOT NULL;

INSERT INTO LaunchpadDatabaseRevision VALUES (87, 32, 2);

