SET client_min_messages=ERROR;

-- Populated by trigger
ALTER TABLE Person ALTER COLUMN openid_identifier SET NOT NULL;

ALTER TABLE Person ALTER COLUMN account_status SET DEFAULT 10;
ALTER TABLE Person ALTER COLUMN account_status SET NOT NULL;

ALTER TABLE Person ALTER COLUMN personal_standing SET DEFAULT 0;
ALTER TABLE Person ALTER COLUMN personal_standing SET NOT NULL;

ALTER TABLE Person ALTER COLUMN mailing_list_receive_duplicates
    SET DEFAULT TRUE;
ALTER TABLE Person ALTER COLUMN mailing_list_receive_duplicates SET NOT NULL;

ALTER TABLE Person ALTER COLUMN mailing_list_auto_subscribe_policy
    SET DEFAULT 1;
ALTER TABLE Person ALTER COLUMN mailing_list_auto_subscribe_policy SET NOT NULL;

ALTER TABLE POMsgSet ALTER COLUMN language SET NOT NULL;

INSERT INTO LaunchpadDatabaseRevision VALUES (87, 32, 2);

