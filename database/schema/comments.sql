/*
  Add Comments to Launchpad database
*/

-- Project
COMMENT ON TABLE Project IS 'Project: A DOAP Project. This table is the core of the DOAP section of the Launchpad database. It contains details of a single open source Project and is the anchor point for products, potemplates, and translationefforts.';
COMMENT ON COLUMN Project.owner IS 'The owner of the project will initially be the person who creates this Project in the system. We will encourage upstream project leaders to take on this role. The Project owner is able to edit the project and appoint project administrators (administrators are recorded in the ProjectRole table).';
COMMENT ON COLUMN Project.homepageurl IS 'The home page URL of this project. Note that this could well be the home page of the main product of this project as well, if the project is too small to have a separate home page for project and product.';
COMMENT ON COLUMN Project.wikiurl IS 'This is the URL of a wiki that includes information about the project. It might be a page in a bigger wiki, or it might be the top page of a wiki devoted to this project.';
COMMENT ON COLUMN Project.lastdoap IS 'This column stores a cached copy of the last DOAP description we saw for this project. We cache the last DOAP fragment for this project because there may be some aspects of it which we are unable to represent in the database (such as multiple homepageurl\'s instead of just a single homepageurl) and storing the DOAP file allows us to re-parse it later and recover this information when our database model has been updated appropriately.';



-- Product
COMMENT ON TABLE Product IS 'Product: a DOAP Product. This table stores core information about an open source product. In Launchpad, anything that can be shipped as a tarball would be a product, and in some cases there might be products for things that never actually ship, depending on the project. For example, most projects will have a \'website\' product, because that allows you to file a Malone bug against the project website. Note that these are not actual product releases, which are stored in the ProductRelease table.';
COMMENT ON COLUMN Product.owner IS 'The Product owner would typically be the person who createed this product in Launchpad. But we will encourage the upstream maintainer of a product to become the owner in Launchpad. The Product owner can edit any aspect of the Product, as well as appointing people to specific roles with regard to the Product (see the ProductRole table). Also, the owner can add a new ProductRelease and also edit Rosetta POTemplates associated with this product.';

