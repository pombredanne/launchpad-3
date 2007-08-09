SET client_min_messages=ERROR;

CREATE TABLE productsubscription (
    id serial NOT NULL,
    product int4 NOT NULL,
    subscriber int4 NOT NULL,
    date_created timestamp NOT NULL DEFAULT timezone('UTC'::text, now()),
    CONSTRAINT productsubscription_pkey
        PRIMARY KEY (id),
    CONSTRAINT "$1" FOREIGN KEY (product)
        REFERENCES product (id) MATCH SIMPLE
        ON UPDATE NO ACTION ON DELETE NO ACTION,
    CONSTRAINT "$2" FOREIGN KEY (subscriber)
        REFERENCES person (id) MATCH SIMPLE
        ON UPDATE NO ACTION ON DELETE NO ACTION,
    CONSTRAINT productsubscription_distinct_subscriber
        UNIQUE (product, subscriber)
);

CREATE INDEX productsubscription_subscriber_idx
  ON productsubscription
  USING btree
  (subscriber);

INSERT INTO LaunchpadDatabaseRevision VALUES (99, 0, 0);
