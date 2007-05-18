SET client_min_messages=ERROR;

CREATE INDEX shippingrequest__normalized_address__idx
    ON ShippingRequest(normalized_address);

CREATE INDEX scriptactivity__name__date_started__idx
    ON ScriptActivity(name, date_started);

INSERT INTO LaunchpadDatabaseRevision VALUES (79, 18, 1);

