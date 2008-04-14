SET client_min_messages=ERROR;

CREATE TABLE CommercialSubscription (
    id serial PRIMARY KEY,
    date_created timestamp without time zone DEFAULT timezone('UTC'::text, now()) NOT NULL,
    date_last_modified timestamp without time zone DEFAULT timezone('UTC'::text, now()) NOT NULL,
    date_starts timestamp without time zone NOT NULL,
    date_expires timestamp without time zone NOT NULL,
    status integer NOT NULL DEFAULT 10, -- UNSUBSCRIBED
    product integer NOT NULL,
    registrant integer,
    authorized_by integer,
    whiteboard text,
    sales_system integer,
    sales_system_id text,
    sales_method integer
);

-- Need indexes for people merge
CREATE INDEX commercialsubscription__product__idx
  ON CommercialSubscription(product);

INSERT INTO LaunchpadDatabaseRevision VALUES (121, 99, 0);
