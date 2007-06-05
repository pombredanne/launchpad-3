SET client_min_messages=ERROR;

CREATE TABLE CodeImport (
    id SERIAL PRIMARY KEY,
    date_created TIMESTAMP WITHOUT TIME ZONE
        DEFAULT timezone('UTC', now()) NOT NULL,
    name text NOT NULL UNIQUE,
    product integer REFERENCES Product NOT NULL,
    series integer REFERENCES ProductSeries UNIQUE,
    branch integer REFERENCES Branch,

    review_status integer DEFAULT 1 NOT NULL,

    rcs_type integer NOT NULL,
    svn_branch_url text UNIQUE,
    cvs_root text,
    cvs_module text,

    UNIQUE (cvs_root, cvs_module),

    CONSTRAINT valid_name CHECK (valid_name(name)),
    CONSTRAINT valid_cvs CHECK ((rcs_type <> 1) OR (
        (cvs_root IS NOT NULL) AND (cvs_root <> '') AND
        (cvs_module IS NOT NULL) AND (cvs_module <> ''))),
    CONSTRAINT null_cvs CHECK ((rcs_type = 1) OR (
        (cvs_root IS NULL) AND (cvs_module IS NULL))),
    CONSTRAINT valid_svn CHECK ((rcs_type <> 2) OR (
        (svn_branch_url IS NOT NULL) AND (svn_branch_url <> ''))),
    CONSTRAINT null_svn CHECK ((rcs_type = 2) OR (svn_branch_url IS NULL)),

    /* XXX: A codeimport can be associated to a product, a productseries and a
       branch. It is not clear at the moment how we should model this
       association. The opinion of the DBA is sought.

       Important use cases include:

       * Object lifecycle: 
         * When the codemiport is created, it does not have a branch. The
           branch is created when the initial is successful.
         * When the branch is created, we need codeimport.branch to set
           branch.product.
         * When the branch is created, if codeimport.series is set, we will set
           codeimport.series.branch to point at the new branch.

       * Querying the database:
         * Display the product on the code-imports listing.
         * Display the product, series and branch on the code-import page.
         * Display code-imports on the product page.
         * Display current and pending code-imports on the series page.

       * Changing object associations:
         * Removing the association between a productseries and an import
           branch.
         * Associating an existing import branch to a productseries. 
         * Changing the product associated to an import and its branch.

       One must also keep in mind that eventually we will support code-imports
       without an associated product.

       This association can be modelled in at least three different ways that
       involves different trade-offs.

       * At most one of branch, series and product foreign keys can be
         non-NULL. When the branch is created, product and series are set to
         NULL.
         * Simplest database constraint.
         * Easy to change object associations.
         * Complicated database queries to retrieve information.

      * The branch, series and product foreign keys are always set if they are
        meaningful.
        * Complicated database constraints to ensure that
          codeimport.series.product codeimport.branch.product and
          codeimport.product are the same.
        * Complicated to change object associations.
        * Simple database queries.

      * The product foreign key is always set, the series foreign key is
        cleared when the branch is published.
        * Trade-off in complication between the two other cases.
        * This is the current design.

      Stuart, which design do you think is better? Can you propose another,
      better design?

      -- David Allouche 2007-06-05
      */

    CONSTRAINT series_or_branch CHECK (
	NOT (branch IS NOT NULL AND series IS NOT NULL))

    /* XXX: If using this design, how to ensure that product == branch.product
       and product == series.product? -- David Allouche 2007-06-05 */

);

-- XXX: This should be fixed once we get a real patch number:
-- MichaelHudson, 2007-05-15
INSERT INTO LaunchpadDatabaseRevision VALUES (87, 88, 0);
