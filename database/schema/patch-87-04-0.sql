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

  -- dropping landing target and diff columns as they will
  -- be implemented in a separate table
ALTER TABLE Branch DROP COLUMN landing_target;
ALTER TABLE Branch DROP COLUMN current_delta_url;
ALTER TABLE Branch DROP COLUMN current_conflicts_url;
ALTER TABLE Branch DROP COLUMN current_diff_adds;
ALTER TABLE Branch DROP COLUMN current_diff_deletes;
ALTER TABLE Branch DROP COLUMN stats_updated;
ALTER TABLE Branch DROP COLUMN current_activity;

INSERT INTO LaunchpadDatabaseRevision VALUES (87, 04, 0);

