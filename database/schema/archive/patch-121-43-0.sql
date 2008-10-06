SET client_min_messages=ERROR;

CREATE TABLE CommercialSubscription (
    id serial PRIMARY KEY,
    date_created timestamp without time zone
        DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'UTC') NOT NULL,
    date_last_modified timestamp without time zone
        DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'UTC') NOT NULL,
    date_starts timestamp without time zone NOT NULL,
    date_expires timestamp without time zone NOT NULL,
    status integer NOT NULL DEFAULT 10, -- UNSUBSCRIBED
    product integer NOT NULL
        CONSTRAINT commercialsubscription__product__fk REFERENCES Product,
    -- Who redeemed the voucher to register the project.
    registrant integer NOT NULL
        CONSTRAINT commercialsubscription__registrant__fk REFERENCES Person,
    purchaser integer NOT NULL    -- Who actually purchased the voucher.
        CONSTRAINT commercialsubscription__purchaser__fk REFERENCES Person,
    whiteboard text,
    sales_system_id text          -- Identifier in the sales system.
                                  -- For Salesforce it will be the
                                  -- voucher number.
);

CREATE INDEX commercialsubscription__registrant__idx
    ON CommercialSubscription (registrant);
CREATE INDEX commercialsubscription__purchaser__idx
    ON CommercialSubscription (purchaser);
CREATE INDEX commercialsubscription__product__idx
    ON CommercialSubscription (product);
CREATE INDEX commercialsubscription__sales_system_id__idx
    ON CommercialSubscription (sales_system_id);

-- Add a new column to the Product table for administrative
-- approval of an 'Other' license.
ALTER TABLE Product
    ADD COLUMN license_approved boolean NOT NULL DEFAULT FALSE;

INSERT INTO LaunchpadDatabaseRevision VALUES (121, 43, 0);
