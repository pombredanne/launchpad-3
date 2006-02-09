SET client_min_messages=ERROR;

CREATE INDEX shippingrequest_daterequested_untriaged
ON ShippingRequest(daterequested)
WHERE cancelled IS FALSE AND approved IS NULL;

INSERT INTO LaunchpadDatabaseRevision VALUES (40, 17, 1);

