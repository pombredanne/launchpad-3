
INSERT INTO CodeImport (name, product, rcs_type, svn_branch_url, review_status, branch)
       (SELECT 'gnome-terminal-trunk-1', product.id, 2,
               'http://svn.example.org/svnroot/gnome-terminal/trunk', 20, branch.id
        FROM product
        JOIN branch on branch.product = product.id
        WHERE product.name='gnome-terminal' and branch.url like '%main');

INSERT INTO CodeImport (name, product, series, rcs_type, cvs_root, cvs_module)
       (SELECT 'a52dec-trunk-3', series.product, series.id, 1, 'cvs.example.org/cvsroot', 'a52dec'
        FROM productseries as series
        JOIN product on series.product=product.id
        WHERE product.name='a52dec' AND series.name='trunk');
