
/*
  Having project as a mandatory organisational structure on products was a
  bad idea. This patch removes the requirement that you have a project to
  add a product.

  STUB: this one is good to go, there were no duplicate product names when
  we checked today (Wed 1/12/04) so hopefully there won't be when we do the
  production update ;-)

*/

-- remove the project NOT NULL constraint
ALTER TABLE Product ALTER COLUMN project DROP NOT NULL;

-- now we need to be able to traverse directly to product so let's make sure
-- that product names are unique
ALTER TABLE Product ADD UNIQUE (name);


