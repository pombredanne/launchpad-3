/* Copyright 2010 Canonical Ltd.  This software is licensed under the
 * GNU Affero General Public License version 3 (see the file LICENSE).
 *
 * Test driver for productseries_setbranch.js.
 *
 */

YUI({
    base: '../../../icing/yui/',
    filter: 'raw', combine: false
    }).use('node-event-simulate', 'test', 'console',
           'registry.productseries_setbranch', function(Y) {

    var module = Y.registry.productseries_setbranch;
    var suite = new Y.Test.Suite("productseries_setbranch Tests");

    suite.add(new Y.Test.Case({
        // Test the onclick results.
        name: 'select_branch_type',

        _should: {
            error: {
                //test_config_undefined: true,
                //test_missing_tbody_is_an_error: true
                }
            },

        setUp: function() {
           this.tbody = Y.one('#productseries-setbranch');
           this.branch_type = this.tbody.all('input[name="field.branch_type"]');
           this.link_lp_bzr = this.branch_type.item(0);
           this.create_new = this.branch_type.item(1);
           this.import_external = this.branch_type.item(2);
           this.branch_location = this.tbody.all('input[name="field.branch_location"]');
        },

        tearDown: function() {
            delete this.tbody;
            //module._milestone_row_uri_template = null;
            //module._tbody = null;
            },
        test_handlers_connected: function() {
           Y.Assert.areEqual('updateBranchType()',
                             this.link_lp_bzr.getAttribute('onclick'),
                             'branch type onclick handler not correct');
           Y.Assert.areEqual('updateBranchType()',
                             this.create_new.getAttribute('onclick'),
                             'branch type onclick handler not correct');

        },
        test_select_link_lp_bzr: function() {
           var field = Y.DOM.byId('field.branch_type.0');
           field.checked = true;
           module.updateBranchType();
           var branch_location = Y.DOM.byId('field.branch_location');
           alert(branch_location.disabled);
           Y.Assert.isFalse(branch_location.disabled,
                            'branch_location disabled');
        },
        test_select_create_new: function() {
           var field = Y.DOM.byId('field.branch_type.1');
           field.checked = true;
           module.updateBranchType();
           var branch_location = Y.DOM.byId('field.branch_location');
           alert(branch_location.disabled);
           Y.Assert.isTrue(branch_location.disabled,
                           'branch_location is not disabled');
        },

        test_select_import_external_bzr: function() {

           // Select import_external as branch_type
           // Select bzr as rcs_type
           // Verify branch_location is disabled
           // Verify cvs_module is disabled
        },

        test_select_import_external_hg: function() {

           // Select import_external as branch_type
           // Select hg as rcs_type
           // Verify branch_location is disabled
           // Verify cvs_module is disabled
        },

        test_select_import_external_git: function() {

           // Select import_external as branch_type
           // Select git as rcs_type
           // Verify branch_location is disabled
           // Verify cvs_module is disabled
        },

        test_select_import_external_svn: function() {

           // Select import_external as branch_type
           // Select svn as rcs_type
           // Verify branch_location is disabled
           // Verify cvs_module is disabled
        },

        test_select_import_external_cvs: function() {

           // Select import_external as branch_type
           // Select cvs as rcs_type
           // Verify branch_location is disabled
           // Verify cvs_module is enabled
        }

        }));

    // Lock, stock, and two smoking barrels.
    Y.Test.Runner.add(suite);

    var console = new Y.Console({newestOnTop: false});
    console.render('#log');

    Y.on('domready', function() {
        Y.Test.Runner.run();
        });
});
