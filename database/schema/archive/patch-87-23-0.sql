SET client_min_messages=ERROR;

CREATE TABLE FAQ (
    id  SERIAL PRIMARY KEY,
    title TEXT NOT NULL,
    tags TEXT,
    content TEXT NOT NULL,
    product INTEGER REFERENCES Product,
    distribution INTEGER REFERENCES Distribution,
    owner INTEGER NOT NULL REFERENCES Person,
    date_created TIMESTAMP WITHOUT TIME ZONE
        NOT NULL DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'UTC'),
    last_updated_by INTEGER REFERENCES Person,
    date_last_updated TIMESTAMP WITHOUT TIME ZONE,
    CONSTRAINT product_or_distro
        CHECK ((product IS NULL) <> (distribution IS NULL))
);

CREATE INDEX faq__product__idx ON FAQ (product)
    WHERE product IS NOT NULL;
CREATE INDEX faq__distribution__idx ON FAQ (distribution)
    WHERE distribution IS NOT NULL;

/* IQuestion.faq links to FAQ document. */
ALTER TABLE Question ADD faq INTEGER;
ALTER TABLE Question
    ADD CONSTRAINT question__faq__fk
        FOREIGN KEY (faq) REFERENCES FAQ(id);
CREATE INDEX question__faq__idx ON Question (faq) WHERE faq IS NOT NULL;

INSERT INTO LaunchpadDatabaseRevision VALUES (87, 23, 0);
