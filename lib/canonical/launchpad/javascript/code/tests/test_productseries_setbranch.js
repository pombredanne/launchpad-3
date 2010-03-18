/* Copyright 2010 Canonical Ltd.  This software is licensed under the
 * GNU Affero General Public License version 3 (see the file LICENSE).
 *
 * Test driver for productseries_setbranch.js.
 *
 */

YUI({
    base: '../../../icing/yui/',
    filter: 'raw', combine: false
    }).use('node-event-simulate', 'test', 'console', 'Event', 'CustomEvent',
           'lp.code.productseries_setbranch', function(Y) {

    var module = Y.lp.code.productseries_setbranch;
    var suite = new Y.Test.Suite("productseries_setbranch Tests");

    suite.add(new Y.Test.Case({
        // Test the onclick results.
        name: 'select_branchtype',

        _should: {
            error: {
                //test_config_undefined: true,
                //test_missing_tbody_is_an_error: true
                }
        },

        setUp: function() {
           this.tbody = Y.one('#productseries-setbranch');

           Y.after('domready', Y.lp.code.productseries_setbranch.setup);

           // Get the individual branch type radio buttons.
           this.link_lp_bzr = Y.DOM.byId('field.branch_type.0');
           this.create_new = Y.DOM.byId('field.branch_type.1');
           this.import_external = Y.DOM.byId('field.branch_type.2');

           // Get the input widgets.
           this.branch_location = Y.DOM.byId('field.branch_location');
           this.cvs_module = Y.DOM.byId('field.cvs_module');
           this.repo_url = Y.DOM.byId('field.repo_url');

           // Get the individual rcs type radio buttons.
           this.cvs = Y.DOM.byId('field.rcs_type.1');
           this.svn = Y.DOM.byId('field.rcs_type.3');
           this.git = Y.DOM.byId('field.rcs_type.4');
           this.hg = Y.DOM.byId('field.rcs_type.5');
           this.bzr = Y.DOM.byId('field.rcs_type.6');
        },

        tearDown: function() {
            delete this.tbody;
        },

        test_handlers_connected: function() {
           var thing = Y.DOM.byId('field.branch_type.0');
           alert(thing);
           var custom_events = Y.Event.getListeners(thing, 'click');
           alert(custom_events);
           var thing2 = Y.one(Y.DOM.byId('field.branch_type.0'));
           alert(thing2);
           custom_events = Y.Event.getListeners(thing2, 'click');
           alert(custom_events);
           var click_event = custom_events[0];
           var subscribers = click_event.subscribers;
           for (var sub in subscribers) {
              Y.Assert.isTrue(subscribers[sub].contains(module.onclick_branchtype),
                              'branchtype_onclick handler setup');
           }
           Y.Assert.areEqual('onclick_branchtype()',
                             this.create_new.getAttribute('onclick'),
                             'branch type onclick handler not correct');
           Y.Assert.areEqual('onclick_branchtype()',
                             this.import_external.getAttribute('onclick'),
                             'branch type onclick handler not correct');

        },
        test_select_link_lp_bzr: function() {
           this.link_lp_bzr.checked = true;
           module.onclick_branchtype();
           Y.Assert.isFalse(this.branch_location.disabled,
                            'branch_location disabled');
           module.onclick_rcs_type();
           // The CVS module and repo url are disabled.
           Y.Assert.isTrue(this.cvs_module.disabled,
                           'cvs_module not disabled');
           Y.Assert.isTrue(this.repo_url.disabled,
                           'repo_url not disabled');
           // All of the radio buttons are disabled.
           Y.Assert.isTrue(this.cvs.disabled,
                           'cvs button not disabled');
           Y.Assert.isTrue(this.svn.disabled,
                           'svn button not disabled');
           Y.Assert.isTrue(this.git.disabled,
                           'git button not disabled');
           Y.Assert.isTrue(this.hg.disabled,
                           'hg button not disabled');
           Y.Assert.isTrue(this.bzr.disabled,
                           'bzr button not disabled');
        },

        test_select_create_new: function() {
           this.create_new.checked = true;
           module.onclick_branchtype();
           Y.Assert.isTrue(this.branch_location.disabled,
                           'branch_location not disabled');
           Y.Assert.isTrue(this.repo_url.disabled,
                           'repo_url not disabled');
           module.onclick_rcs_type();
           // The CVS module and repo url are disabled.
           Y.Assert.isTrue(this.cvs_module.disabled,
                           'cvs_module not disabled');
           Y.Assert.isTrue(this.repo_url.disabled,
                           'repo_url not disabled');
           // All of the radio buttons are disabled.
           Y.Assert.isTrue(this.cvs.disabled,
                           'cvs button not disabled');
           Y.Assert.isTrue(this.svn.disabled,
                           'svn button not disabled');
           Y.Assert.isTrue(this.git.disabled,
                           'git button not disabled');
           Y.Assert.isTrue(this.hg.disabled,
                           'hg button not disabled');
           Y.Assert.isTrue(this.bzr.disabled,
                           'bzr button not disabled');
        },

        test_select_import_external: function() {
           this.import_external.checked = true;
           module.onclick_branchtype();
           Y.Assert.isTrue(this.branch_location.disabled,
                           'branch_location not disabled');
           Y.Assert.isFalse(this.repo_url.disabled,
                           'repo_url disabled');
           module.onclick_rcs_type();
           // All of the radio buttons are disabled.
           Y.Assert.isFalse(this.cvs.disabled,
                           'cvs button disabled');
           Y.Assert.isFalse(this.svn.disabled,
                           'svn button disabled');
           Y.Assert.isFalse(this.git.disabled,
                           'git button disabled');
           Y.Assert.isFalse(this.hg.disabled,
                           'hg button disabled');
           Y.Assert.isFalse(this.bzr.disabled,
                           'bzr button disabled');

        },

        test_select_import_external_bzr: function() {
           this.import_external.checked = true;
           module.onclick_branchtype();
           Y.Assert.isFalse(this.repo_url.disabled,
                           'repo_url disabled');
           this.bzr.checked = true;
           module.onclick_rcs_type();
           // The CVS module input is disabled.
           Y.Assert.isTrue(this.cvs_module.disabled,
                           'cvs_module disabled');
        },

        test_select_import_external_hg: function() {
           this.import_external.checked = true;
           module.onclick_branchtype();
           Y.Assert.isFalse(this.repo_url.disabled,
                           'repo_url disabled');
           this.hg.checked = true;
           module.onclick_rcs_type();
           // The CVS module input is disabled.
           Y.Assert.isTrue(this.cvs_module.disabled,
                           'cvs_module disabled');
        },

        test_select_import_external_git: function() {
           this.import_external.checked = true;
           module.onclick_branchtype();
           Y.Assert.isFalse(this.repo_url.disabled,
                           'repo_url disabled');
           this.git.checked = true;
           module.onclick_rcs_type();
           // The CVS module input is disabled.
           Y.Assert.isTrue(this.cvs_module.disabled,
                           'cvs_module disabled');
        },

        test_select_import_external_svn: function() {
           this.import_external.checked = true;
           module.onclick_branchtype();
           Y.Assert.isFalse(this.repo_url.disabled,
                           'repo_url disabled');
           this.svn.checked = true;
           module.onclick_rcs_type();
           // The CVS module input is disabled.
           Y.Assert.isTrue(this.cvs_module.disabled,
                           'cvs_module disabled');
        },

        test_select_import_external_cvs: function() {
           this.import_external.checked = true;
           module.onclick_branchtype();
           Y.Assert.isFalse(this.repo_url.disabled,
                           'repo_url disabled');
           this.cvs.checked = true;
           module.onclick_rcs_type();
           // The CVS module input is enabled
           Y.Assert.isFalse(this.cvs_module.disabled,
                           'cvs_module disabled');
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
