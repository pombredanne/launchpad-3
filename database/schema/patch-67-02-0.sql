SET client_min_messages=ERROR;

CREATE TABLE PillarName (
    id serial PRIMARY KEY,
    name text UNIQUE CONSTRAINT valid_name CHECK (valid_name(name)),
    product int REFERENCES Product,
    project int REFERENCES Project,
    distribution int REFERENCES Distribution,
    CONSTRAINT only_one_target CHECK (
        (product IS NOT NULL AND project IS NULL AND distribution IS NULL)
        OR (product IS NULL AND project IS NOT NULL AND distribution IS NULL)
        OR (product IS NULL AND project IS NULL AND distribution IS NOT NULL)
        )
    );

-- Create PillarName entries for our distributions.
INSERT INTO PillarName (name, distribution)
    SELECT name, id FROM Distribution
    WHERE id NOT IN (
        SELECT distribution FROM PillarName WHERE distribution IS NOT NULL
        )
    ORDER BY id;

-- Create PillarName entries for our products that have name conflicts
-- with distributions.
INSERT INTO PillarName (name, product)
    SELECT name || '-product', id FROM Product
    WHERE (name, id) NOT IN (
        SELECT name, product FROM PillarName WHERE product IS NOT NULL
        )
        AND name IN (SELECT name FROM PillarName)
    ORDER BY id;

-- Create PillarName entries for the rest of our products.
INSERT INTO PillarName (name, product)
    SELECT name, id FROM Product
    WHERE id NOT IN (SELECT product FROM PillarName WHERE product IS NOT NULL)
    ORDER BY id;

-- Create PillarName entries for our projects that have name conflicts
-- with distributions or products.
INSERT INTO PillarName (name, project)
    SELECT name || '-project', id FROM Project
    WHERE (name, id) NOT IN (
        SELECT name, project FROM PillarName WHERE project IS NOT NULL
        )
        AND name IN (SELECT name FROM PillarName);

-- Create PillarName entries for the rest of our projects.
INSERT INTO PillarName (name, project)
    SELECT name, id FROM Project
    WHERE id NOT IN (SELECT project FROM PillarName WHERE project IS NOT NULL);

-- Fix up any product names we were forced to change
UPDATE Product SET name=PillarName.name
FROM PillarName
WHERE Product.id = PillarName.product AND Product.name != PillarName.name;

-- Fix up any project names we were forced to change
UPDATE Project SET name=PillarName.name
FROM PillarName
WHERE Project.id = PillarName.project AND Project.name != PillarName.name;

INSERT INTO LaunchpadDatabaseRevision VALUES (67, 02, 0);
