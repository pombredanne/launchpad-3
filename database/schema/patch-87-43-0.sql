SET client_min_messages=ERROR;

CREATE TABLE ProductSubscription (
    id serial PRIMARY KEY,
    product integer NOT NULL,
    subscriber integer NOT NULL,
    date_created timestamp without time zone NOT NULL
        DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'UTC'),
    CONSTRAINT productsubscription__product__fk FOREIGN KEY (product)
        REFERENCES Product,
    CONSTRAINT productsubscription__subscriber__fk FOREIGN KEY (subscriber)
        REFERENCES Person,
    CONSTRAINT productsubscription__product__subscriber__key
        UNIQUE (product, subscriber)
);

CREATE INDEX productsubscription__subscriber__idx
  ON productsubscription (subscriber);

INSERT INTO LaunchpadDatabaseRevision VALUES (87, 43, 0);
