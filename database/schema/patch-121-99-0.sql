SET client_min_messages=ERROR;

CREATE TABLE CommercialSubscription (
    id serial PRIMARY KEY,
    date_created timestamp without time zone DEFAULT timezone('UTC'::text, now()) NOT NULL,
    date_last_modified timestamp without time zone DEFAULT timezone('UTC'::text, now()) NOT NULL,
    date_starts timestamp without time zone NOT NULL,
    date_expires timestamp without time zone NOT NULL,
    status integer NOT NULL DEFAULT 10, -- UNSUBSCRIBED
    product integer NOT NULL,
    registrant integer NOT NULL,  -- Who redeemed the voucher to register the project.
    purchaser integer NOT NULL,   -- Who actually purchased the voucher.
    whiteboard text,
    sales_system integer,
    sales_system_id text          -- Identifier in the sales system.  For Salesforce it will be the
                                  -- voucher number.
);

-- Need indexes for people merge
CREATE INDEX commercialsubscription__product__idx
  ON CommercialSubscription(product);

-- Add a new column to the Product table for administrative
-- approval of an 'Other' license.
ALTER TABLE Product
    ADD COLUMN manually_approved_license boolean NOT NULL DEFAULT FALSE;

INSERT INTO LaunchpadDatabaseRevision VALUES (121, 99, 0);
