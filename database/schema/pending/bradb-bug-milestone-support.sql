CREATE TABLE Milestone (
    id SERIAL PRIMARY KEY,
    product INT NOT NULL,
    name TEXT NOT NULL,
    title TEXT NOT NULL,

    CONSTRAINT milestone_product_fk FOREIGN KEY (product) REFERENCES Product (id)
);

COMMENT ON TABLE Milestone IS 'An identifier that helps a maintainer group together things in some way, e.g. "1.2" could be a Milestone that bazaar developers could use to mark a task as needing fixing in bazaar 1.2.';
COMMENT ON COLUMN Milestone.product IS 'The product for which this is a milestone.';
COMMENT ON COLUMN Milestone.name IS 'The identifier text, e.g. "1.2."';
COMMENT ON COLUMN Milestone.title IS 'The description of, e.g. "1.2."';

ALTER TABLE BugTask ADD COLUMN milestone INT NULL;

COMMENT ON COLUMN BugTask.milestone IS 'A way to mark a bug for grouping purposes, e.g. to say it needs to be fixed by version 1.2';
