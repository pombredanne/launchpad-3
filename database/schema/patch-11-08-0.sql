SET client_min_messages=ERROR;


CREATE TABLE POTemplateName (
  id        serial PRIMARY KEY,
  name      text NOT NULL,
  title     text NOT NULL,
  description text,
  CONSTRAINT potemplate_name_key UNIQUE(name),
  CONSTRAINT potemplate_valid_name CHECK(valid_name(name))
);

ALTER TABLE POTemplate ADD COLUMN potemplatename integer
    CONSTRAINT potemplate_potemplatename_fk REFERENCES POTemplateName(id);
ALTER TABLE POTemplate ADD COLUMN productrelease integer 
    CONSTRAINT potemplate_productrelease_fk REFERENCES ProductRelease(id);

ALTER TABLE POTemplate ADD CONSTRAINT potemplate_productrelease_key 
    UNIQUE(productrelease, potemplatename);
ALTER TABLE POTemplate ADD CONSTRAINT potemplate_distrorelease_key
    UNIQUE(distrorelease, sourcepackagename, potemplatename);

ALTER TABLE POTemplate DROP CONSTRAINT potemplate_rawimportstatus_valid;

/* Migration */

-- Set the owner to rosetta-admins
UPDATE POTemplate SET owner=Person.id
    FROM Person
    WHERE Person.name='rosetta-admins' AND POTemplate.owner IS NULL;

-- Add entries to POTemplateName, and update the POTemplates to reference them
INSERT INTO POTemplateName (name, title)  (
    SELECT name, min(title) FROM POTemplate GROUP BY name
    );
UPDATE POTemplate SET potemplatename=POTemplateName.id
    FROM POTemplateName WHERE POTemplateName.name=POTemplate.name;
ALTER TABLE POTemplate DROP CONSTRAINT valid_name;

-- We can now only link to productrelease OR (distrorelease/sourcepackagename)
ALTER TABLE POTemplate ALTER product DROP NOT NULL;
UPDATE POTemplate SET product=NULL WHERE product IS NOT NULL AND distrorelease IS NOT NULL AND sourcepackagename IS NOT NULL;

-- Add dummy ProductRelease
INSERT INTO ProductRelease (product, datereleased, version, owner) (
    SELECT DISTINCT
        Product.id,
        CURRENT_TIMESTAMP AT TIME ZONE 'UTC',
        'unknown',
        Product.owner
    FROM
        Product JOIN POTemplate ON Product.id = POTemplate.product
    WHERE
        POTemplate.sourcepackagename IS NULL
        AND Product.id NOT IN (SELECT product FROM ProductRelease)
    );

-- Link POTemplates to ProductRelease instead of Product
UPDATE POTemplate SET productrelease=(
    SELECT min(ProductRelease.id)
    FROM ProductRelease JOIN Product ON ProductRelease.product=product.id
    WHERE Product.id = POTemplate.product
    );

-- Fix NULLs - probably creating duds that will need to be manually pruned
-- from the UI.
UPDATE POTemplate SET rawfile='' WHERE rawfile IS NULL;
UPDATE POTemplate SET rawimporter=owner WHERE rawimporter IS NULL;
UPDATE POTemplate SET daterawimport=CURRENT_TIMESTAMP AT TIME ZONE 'UTC'
    WHERE daterawimport IS NULL;

ALTER TABLE POTemplate ALTER COLUMN owner SET NOT NULL;
ALTER TABLE POTemplate ALTER COLUMN potemplatename SET NOT NULL;
ALTER TABLE POTemplate ALTER COLUMN rawfile SET NOT NULL;
ALTER TABLE POTemplate ALTER COLUMN rawimporter SET NOT NULL;
ALTER TABLE POTemplate ALTER COLUMN daterawimport SET NOT NULL;

ALTER TABLE POTemplate ADD CONSTRAINT valid_link CHECK (
    (productrelease IS NULL <> distrorelease IS NULL)
    AND (distrorelease IS NULL = sourcepackagename IS NULL)
    );

ALTER TABLE POTemplate DROP COLUMN product;
ALTER TABLE POTemplate DROP COLUMN branch;
ALTER TABLE POTemplate DROP COLUMN changeset;
ALTER TABLE POTemplate DROP COLUMN sourcepackagerelease;
ALTER TABLE POTemplate DROP COLUMN name;


-- Rename some constraints
ALTER TABLE POTemplate DROP CONSTRAINT "$4";
ALTER TABLE POTemplate ADD CONSTRAINT potemplate_license_fk
    FOREIGN KEY (license) REFERENCES License;
ALTER TABLE POTemplate DROP CONSTRAINT "$5";
ALTER TABLE POTemplate ADD CONSTRAINT potemplate_owner_fk
    FOREIGN KEY (owner) REFERENCES Person;
ALTER TABLE POTemplate DROP CONSTRAINT "$7";
ALTER TABLE POTemplate ADD CONSTRAINT potemplate_rawimporter_fk
    FOREIGN KEY (rawimporter) REFERENCES Person;


INSERT INTO LaunchpadDatabaseRevision VALUES (11, 8, 0);

