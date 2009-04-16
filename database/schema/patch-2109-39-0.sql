SET client_min_messages=ERROR;

DROP INDEX oauthnonce__access_token__request_timestamp__idx;
ALTER TABLE OAuthNonce
    DROP CONSTRAINT oauthnonce__none__access_token__request_timestamp__key,
    ADD CONSTRAINT oauthnonce__access_token__request_timestamp__nonce__key
        UNIQUE (access_token, request_timestamp, nonce);
CLUSTER OAuthNonce
    USING oauthnonce__access_token__request_timestamp__nonce__key;

INSERT INTO LaunchpadDatabaseRevision VALUES (2109, 39, 0);
