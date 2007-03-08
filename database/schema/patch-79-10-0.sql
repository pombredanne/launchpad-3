SET client_min_messages=ERROR;

-- Deleting unused columns from the Branch table

ALTER TABLE Branch DROP COLUMN branch_product_name;
  -- confirm none not null

ALTER TABLE Branch DROP COLUMN product_locked;
  -- confirm none True

ALTER TABLE Branch DROP COLUMN branch_home_page;
  -- confirm none not null

ALTER TABLE Branch DROP COLUMN home_page_locked;
  -- confirm none True (is nullable column with a default)

ALTER TABLE Branch DROP COLUMN cache_url;
  -- confirm none not null

ALTER TABLE Branch DROP COLUMN started_at;
  -- confirm none not null


INSERT INTO LaunchpadDatabaseRevision VALUES (79, 10, 0);

