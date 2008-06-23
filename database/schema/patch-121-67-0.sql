SET client_min_messages=ERROR;


-- Add support for a legacy identifier. After adding code to ensure newly
-- generated ids are 'new' format and that both openid_identifier and
-- old_openid_identifier work, we can migrate the existing ids and generate
-- 'new' format ones for all the existing users.
-- We can probably drop this column sometime in the future once we detect
-- they are no longer being used. Or perhaps we should keep it to allow
-- 'change once, and only once' behavior.
ALTER TABLE Account ADD COLUMN old_openid_identifier text;

CREATE INDEX account__old_openid_identifier__idx
    ON Account (old_openid_identifier);

INSERT INTO LaunchpadDatabaseRevision VALUES (121, 67, 0);

