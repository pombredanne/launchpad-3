/*
  Add Comments to Launchpad database
*/

-- Project
COMMENT ON TABLE Project IS 'Project: A DOAP Project. This table is the core of the DOAP section of the Launchpad database. It contains details of a single open source Project and is the anchor point for products, potemplates, and translationefforts.';
COMMENT ON COLUMN Project.owner IS 'The owner of the project will initially be the person who creates this Project in the system. We will encourage upstream project leaders to take on this role. The Project owner is able to edit the project and appoint project administrators (administrators are recorded in the ProjectRole table).';
COMMENT ON COLUMN Project.homepageurl IS 'The home page URL of this project. Note that this could well be the home page of the main product of this project as well, if the project is too small to have a separate home page for project and product.';
COMMENT ON COLUMN Project.wikiurl IS 'This is the URL of a wiki that includes information about the project. It might be a page in a bigger wiki, or it might be the top page of a wiki devoted to this project.';
COMMENT ON COLUMN Project.lastdoap IS 'This column stores a cached copy of the last DOAP description we saw for this project. We cache the last DOAP fragment for this project because there may be some aspects of it which we are unable to represent in the database (such as multiple homepageurl\'s instead of just a single homepageurl) and storing the DOAP file allows us to re-parse it later and recover this information when our database model has been updated appropriately.';
COMMENT ON COLUMN Project.name IS 'A short lowercase name uniquely identifying the product. Use cases include being used as a key in URL traversal.';


-- ProjectRelationship
COMMENT ON TABLE ProjectRelationship IS 'Project Relationships. This table stores information about the way projects are related to one another in the open source world. The actual nature of the relationship is stored in the \'label\' field, and possible values are given by the ProjectRelationship enum in dbschema.py. Examples are AGGREGATES ("the Gnome Project AGGREGATES EOG and Evolution and Gnumeric and AbiWord") and SIMILAR ("the Evolution project is SIMILAR to the Mutt project").';
COMMENT ON COLUMN ProjectRelationship.subject IS 'The subject of the relationship. Relationships are generally unidirectional - A AGGREGATES B is not the same as B AGGREGATES A. In the example "Gnome AGGREGATES Evolution", Gnome is the subject.';
COMMENT ON COLUMN ProjectRelationship.object IS 'The object of the relationship. In the example "Gnome AGGREGATES Evolution", Evolution is the object.';
COMMENT ON COLUMN ProjectRelationship.label IS 'The nature of the relationship. This integer takes one of the values enumerated in dbschema.py ProjectRelationship';

-- EmailAddress
COMMENT ON COLUMN EmailAddress.email IS 'An email address used by a Person. The email address is stored in a casesensitive way, but must be case insensitivly unique.';

-- ProjectRole
COMMENT ON TABLE ProjectRole IS 'Project Roles. This table records the explicit roles that people play in an open source project, with the exception of the \'ownership\' role, which is encoded in Project.owner. Types of roles are enumerated in dbschema.py DOAPRole.';
COMMENT ON COLUMN ProjectRole.person IS 'The person playing the role.';
COMMENT ON COLUMN ProjectRole.role IS 'The role, an integer enumeration documented in dbschema.py ProjectRole.';
COMMENT ON COLUMN ProjectRole.project IS 'The project in which the person plays a role.';


-- Product
COMMENT ON TABLE Product IS 'Product: a DOAP Product. This table stores core information about an open source product. In Launchpad, anything that can be shipped as a tarball would be a product, and in some cases there might be products for things that never actually ship, depending on the project. For example, most projects will have a \'website\' product, because that allows you to file a Malone bug against the project website. Note that these are not actual product releases, which are stored in the ProductRelease table.';
COMMENT ON COLUMN Product.owner IS 'The Product owner would typically be the person who createed this product in Launchpad. But we will encourage the upstream maintainer of a product to become the owner in Launchpad. The Product owner can edit any aspect of the Product, as well as appointing people to specific roles with regard to the Product (see the ProductRole table). Also, the owner can add a new ProductRelease and also edit Rosetta POTemplates associated with this product.';
COMMENT ON COLUMN Product.project IS 'Every Product belongs to one and only one Project, which is referenced in this column.';
COMMENT ON COLUMN Product.listurl IS 'This is the URL where information about a mailing list for this Product can be found. The URL might point at a web archive or at the page where one can subscribe to the mailing list.';
COMMENT ON COLUMN Product.programminglang IS 'This field records, in plain text, the name of any significant programming languages used in this product. There are no rules, conventions or restrictions on this field at present, other than basic sanity. Examples might be "Python", "Python, C" and "Java".';
COMMENT ON COLUMN Product.downloadurl IS 'The download URL for a Product should be the best place to download that product, typically off the relevant Project web site. This should not point at the actual file, but at a web page with download information.';
COMMENT ON COLUMN Product.lastdoap IS 'This column stores a cached copy of the last DOAP description we saw for this product. See the Project.lastdoap field for more info.';
-- COMMENT ON COLUMN Product.manifest IS 'The Product manifest, if it exists, tells us exactly which branches are combined to make up the source of this product. Manifests are a Sourcerer invention, mainly used for distribution packaging, but they can apply equally well to an upstream Product. If a manifest exists for this product then this field points to it.';



-- ProductLabel
COMMENT ON TABLE ProductLabel IS 'The Product label table. We have not yet clearly defined the nature of product labels, so please do not refer to this table yet. If you have a need for tags or labels on Products, please contact Mark.';



-- ProductRole
COMMENT ON TABLE ProductRole IS 'Product Roles: this table documents the roles that people play with regard to a specific product. Note that if the project only has one product then it\'s best to document these roles at the project level, not at the product level. If a project has many products, then this table allows you to identify people playing a role that is specific to one of them.';
COMMENT ON COLUMN ProductRole.person IS 'The person playing the role.';
COMMENT ON COLUMN ProductRole.role IS 'The role being played. Valid roles are documented in dbschema.py DOAPRole. The roles are exactly the same as those used for ProjectRole.';
COMMENT ON COLUMN ProductRole.product IS 'The product where the person plays this role.';



-- ProductSeries
COMMENT ON TABLE ProductSeries IS 'A ProductSeries is a set of product releases that are related to a specific version of the product. Typically, each major release of the product starts a new ProductSeries. These often map to a branch in the revision control system of the project, such as "2_0_STABLE". A few conventional Series names are "head" for releases of the HEAD branch, "1.0" for releases with version numbers like "1.0.0" and "1.0.1".';
COMMENT ON COLUMN ProductSeries.name IS 'The name of the ProductSeries is like a unix name, it should not contain any spaces and should start with a letter or number. Good examples are "2.0", "3.0", "head" and "development".';



-- ProductRelease
COMMENT ON TABLE ProductRelease IS 'A Product Release. This is table stores information about a specific \'upstream\' software release, like Apache 2.0.49 or Evolution 1.5.4.';
COMMENT ON COLUMN ProductRelease.version IS 'This is a text field containing the version string for this release, such as \'1.2.4\' or \'2.0.38\' or \'7.4.3\'.';
COMMENT ON COLUMN ProductRelease.title IS 'This is the GSV Name of this release, like \'The Warty Warthog Release\' or \'All your base-0 are belong to us\'. Many upstream projects are assigning fun names to their releases - these go in this field.';




/*
  Rosetta
*/



/*
  Buttress
*/



/*
  Malone
*/
COMMENT ON COLUMN Bug.name IS 
    'A lowercase name uniquely identifying the bug';


/*
  Soyuz
*/
-- Are these soyuz or butress?
COMMENT ON COLUMN Sourcepackage.sourcepackagename IS 
    'A lowercase name identifying the sourcepackage';
COMMENT ON COLUMN SourcepackageName.name IS
    'A lowercase name identifying one or more sourcepackages';
COMMENT ON COLUMN BinarypackageName.name IS
    'A lowercase name identifying one or more binarypackages';


/* Lucille's configuration */

COMMENT ON COLUMN distribution.lucilleconfig IS 'Configuration
information which lucille will use when processing uploads and
generating archives for this distribution';

COMMENT ON COLUMN distrorelease.lucilleconfig IS 'Configuration
information which lucille will use when processing uploads and
generating archives for this distro release';


COMMENT ON COLUMN ArchArchive.name IS 'The archive name, usually in the format of an email address';

