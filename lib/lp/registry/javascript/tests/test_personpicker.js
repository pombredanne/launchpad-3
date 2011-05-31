/* Copyright 2011 Canonical Ltd.  This software is licensed under the
 * GNU Affero General Public License version 3 (see the file LICENSE).
 */

YUI({
    base: '../../../../canonical/launchpad/icing/yui/',
    filter: 'raw', combine: false,
    fetchCSS: false
    }).use('test', 'console', 'plugin', 'lp.registry.personpicker',
           'node-event-simulate', function(Y) {

    var suite = new Y.Test.Suite("lp.registry.personpicker Tests");

    suite.add(new Y.Test.Case({
        name: 'personpicker',

        setUp: function() {
            window.LP = {
                links: {me: '/~no-one'},
                cache: {}
            }
        },

        test_render: function () {
            var personpicker = new Y.lp.registry.personpicker.PersonPicker();
            personpicker.render();
            personpicker.show();
            
            // The extra buttons section exists
            Y.Assert.isNotNull(Y.one('.extra-form-buttons'));
            Y.Assert.isNotNull(Y.one('.yui-picker-remove-button'));
            Y.Assert.isNotNull(Y.one('.yui-picker-assign-me-button'));
        },
        
        test_buttons: function () {
            var personpicker = new Y.lp.registry.personpicker.PersonPicker();
            personpicker.render();
            personpicker.show();
           
            // Patch the picker so the assign_me and remove methods can be 
            // tested.
            var data = null;
            personpicker.on('save', function (result) {
                data = result.value;
            });
            var remove = Y.one('.yui-picker-remove-button');
            remove.simulate('click');
            Y.Assert.areEqual('', data);

            var assign_me = Y.one('.yui-picker-assign-me-button');
            assign_me.simulate('click');
            Y.Assert.areEqual('no-one', data);
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

