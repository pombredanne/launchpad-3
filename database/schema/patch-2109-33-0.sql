SET client_min_messages=ERROR;

-- We use nonces to prevent replay attacks, but they can be used only if the
-- access_token is not changed *and* the request_timestamp is not changed, so
-- it doesn't make sense to enforce nonces to be unique across tokens.
ALTER TABLE OauthNonce DROP CONSTRAINT oauthnonce_nonce_token_key;
ALTER TABLE OauthNonce
    ADD CONSTRAINT oauthnonce__none__access_token__request_timestamp__key
        UNIQUE (nonce, access_token, request_timestamp);

INSERT INTO LaunchpadDatabaseRevision VALUES (2109, 33, 0);
