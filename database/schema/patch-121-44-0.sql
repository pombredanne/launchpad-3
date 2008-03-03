SET client_min_messages=ERROR;

-- Replay attacks may only be dangerous when the consumer already has an
-- access token (since all the previous steps are done over SSL), so we only
-- need to store the nonces that come associated with an access token.
ALTER TABLE OauthNonce 
    ADD COLUMN access_token integer REFERENCES OAuthAccessToken;
ALTER TABLE OauthNonce DROP COLUMN consumer;

-- We use nonces to prevent replay attacks, but they can be done only if the
-- access_token is not changed, so it doesn't make sense to enforce nonces to
-- be unique across tokens.
ALTER TABLE OauthNonce DROP CONSTRAINT oauthnonce_nonce_key;
ALTER TABLE OauthNonce
    ADD CONSTRAINT oauthnonce_nonce_token_key UNIQUE (nonce, access_token);

INSERT INTO LaunchpadDatabaseRevision VALUES (121, 44, 0);
