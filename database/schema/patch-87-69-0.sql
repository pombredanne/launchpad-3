SET client_min_messages=ERROR;

CREATE TABLE FAQ (
    id  SERIAL PRIMARY KEY,
    title TEXT NOT NULL,
    summary TEXT NOT NULL,
    keywords TEXT,
    content TEXT NOT NULL,
    url TEXT NOT NULL,
    product INTEGER REFERENCES Product,
    distribution INTEGER REFERENCES Distribution,
    owner INTEGER NOT NULL REFERENCES Person,
    date_created TIMESTAMP WITHOUT TIME ZONE
        DEFAULT timezone('UTC'::text, (
            'now'::text)::timestamp(6) with time zone) NOT NULL,
    last_updated_by INTEGER REFERENCES Person,
    date_last_updated TIMESTAMP WITHOUT TIME ZONE,
    fti ts2.tsvector,
    CONSTRAINT product_or_distro
        CHECK (((product IS NULL) <> (distribution IS NULL))),
    CONSTRAINT content_or_url
        CHECK (((content IS NULL) <> (url IS NULL)))
);

CREATE INDEX faq__fti ON FAQ USING gist (fti ts2.gist_tsvector_ops);
CREATE INDEX faq__product__idx ON FAQ (product);
CREATE INDEX faq__distribution__idx ON FAQ (distribution);

/* IQuestion.faq links to FAQ document. */
ALTER TABLE Question ADD faq INTEGER;
ALTER TABLE Question
    ADD CONSTRAINT question__faq__fk
        FOREIGN KEY (faq) REFERENCES FAQ(id);
CREATE INDEX question__faq__idx ON Question (faq);

INSERT INTO LaunchpadDatabaseRevision VALUES (87, 69, 0);
