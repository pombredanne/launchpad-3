SET client_min_messages TO error;

/*
  Add SourceForge and Freshmeat references to both Project and Product.
  We need it on both because SF and FM don't differentiate between projects
  and products.
*/

ALTER TABLE project ADD COLUMN sourceforgeproject TEXT;
COMMENT ON COLUMN Project.sourceforgeproject IS 'The SourceForge project name for this project. This is not unique as SourceForge doesn\'t use the same project/product structure as DOAP.';
ALTER TABLE project ADD COLUMN freshmeatproject TEXT;
COMMENT ON COLUMN Project.freshmeatproject IS 'The FreshMeat project name for this project. This is not unique as FreshMeat does not have the same project/product structure as DOAP';
ALTER TABLE product ADD COLUMN sourceforgeproject TEXT;
COMMENT ON COLUMN Product.sourceforgeproject IS 'The SourceForge project name for this product. This is not unique as SourceForge doesn\'t use the same project/product structure as DOAP.';
ALTER TABLE product ADD COLUMN freshmeatproject TEXT;
COMMENT ON COLUMN Product.freshmeatproject IS 'The FreshMeat project name for this product. This is not unique as FreshMeat does not have the same project/product structure as DOAP';

