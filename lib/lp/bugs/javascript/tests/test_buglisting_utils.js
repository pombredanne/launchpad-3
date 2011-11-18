/* Copyright (c) 2011, Canonical Ltd. All rights reserved. */

YUI.add('lp.buglisting_utils.test', function(Y) {

var buglisting_utils = Y.namespace('lp.buglisting_utils.test');

var suite = new Y.Test.Suite('BugListingConfigUtil Tests');

var Assert = Y.Assert;
var ArrayAssert = Y.ArrayAssert;
var ObjectAssert = Y.ObjectAssert;

suite.add(new Y.Test.Case({

    name: 'buglisting_display_utils_tests',

    _should: {
        error: {

            test_widget_requires_cache: [
                'LP.cache.field_visibility must be defined ',
                'when using BugListingConfigUtil.'
            ].join('')
        }
    },

    setUp: function() {
        // _setDoc is required for tests using cookies to pass.
        Y.Cookie._setDoc({cookie: ""});
        // Simulate LP.cache.field_visibility which will be
        // present in the actual page.
        window.LP = {
            links: {
                me: 'foobar'
            },

            cache: {
                field_visibility: {
                    show_title: true,
                    show_id: false,
                    show_importance: false,
                    show_status: true,
                    show_bug_heat: true,
                    show_bugtarget: true,
                    show_age: false,
                    show_last_updated: false,
                    show_assignee: false,
                    show_reporter: false,
                    show_milestone_name: false,
                    show_tags: false
                },

                field_visibility_defaults: {
                    show_title: true,
                    show_id: true,
                    show_importance: true,
                    show_status: true,
                    show_bug_heat: true,
                    show_bugtarget: true,
                    show_age: false,
                    show_last_updated: false,
                    show_assignee: false,
                    show_reporter: false,
                    show_milestone_name: false,
                    show_tags: false
                }
            }
        };
        this.cookie_name = this.getCookieName();
    },

    tearDown: function() {
        if (Y.Lang.isValue(this.list_util)) {
            this.list_util.destroy();
        }
        // Cleanup cookies.
        Y.Cookie.remove(this.cookie_name);
        Y.Cookie._setDoc(Y.config.doc);
    },

    /**
     * Test helper to see what the form actually looks
     * like on the page.
     *
     * It builds a list of show_xxx names and another
     * list of booleans representing checked value.
     */
    getActualInputData: function() {
        var actual_names = [];
        var actual_checked = [];
        var inputs = Y.one(
            '.yui3-lazr-formoverlay-content form').all('input');
        inputs.each(function(el) {
            if (el.get('type') === 'checkbox') {
                actual_names.push(el.get('name'));
                actual_checked.push(el.get('checked'));
            }
        });
        return [actual_names, actual_checked];
    },

    getCookieName: function() {
        return LP.links.me + '-buglist-fields';
    },

    test_bug_listing_util_extends_base_util: function() {
        // BugListingConfigUtil extends from BaseConfigUtil.
        this.list_util = new Y.lp.buglisting_utils.BugListingConfigUtil();
        Assert.isInstanceOf(Y.lp.configutils.BaseConfigUtil, this.list_util);
    },

    test_default_field_visibility_config: function() {
        // The default field_visibility must be supplied by LP.cache.
        this.list_util = new Y.lp.buglisting_utils.BugListingConfigUtil();
        var defaults_from_cache = LP.cache.field_visibility_defaults;
        var field_visibility_defaults = this.list_util.get(
            'field_visibility_defaults');
        ObjectAssert.areEqual(defaults_from_cache, field_visibility_defaults);
    },

    test_widget_requires_cache: function() {
        // BugListingConfigUtil requires our JSON cache for
        // field_visibility and will error on render if not found.
        delete window.LP;
        this.list_util = new Y.lp.buglisting_utils.BugListingConfigUtil();
        this.list_util.render();
    },

    test_field_visibility_defaults_readonly: function() {
        // field_visibility_defaults is a readOnly attribute,
        // so field_visibility_defaults will always return the same
        // as LP.cache.field_visibility_defaults.
        this.list_util = new Y.lp.buglisting_utils.BugListingConfigUtil();
        var attempted_defaults = {
            foo: 'bar',
            baz: 'bop'
        };
        this.list_util.set('field_visibility_defaults', attempted_defaults);
        ObjectAssert.areEqual(
            this.list_util.get('field_visibility_defaults'),
            LP.cache.field_visibility_defaults);
    },

    test_supplied_field_visibility_config: function() {
        // field_visibility can be changed at the call site.
        // Supplied fields will be merged with the defaults.
        var supplied_config = {
            show_bug_heat: false,
            show_status: false
        };
        var expected_config = {
            show_title: true,
            show_id: true,
            show_importance: true,
            show_status: false,
            show_bug_heat: false,
            show_bugtarget: true,
            show_age: false,
            show_last_updated: false,
            show_assignee: false,
            show_reporter: false,
            show_milestone_name: false,
            show_tags: false
        };
        this.list_util = new Y.lp.buglisting_utils.BugListingConfigUtil({
            field_visibility: supplied_config
        });
        this.list_util.render();
        ObjectAssert.areEqual(
            expected_config, this.list_util.get('field_visibility'));
    },

    test_cookie_updates_field_visibility_config: function() {
        // If the $USER-buglist-fields cookie is present,
        // the widget will update field_visibility to these values.
        var expected_config = {
            show_title: true,
            show_id: true,
            show_importance: true,
            show_status: true,
            show_bug_heat: false,
            show_bugtarget: false,
            show_age: true,
            show_last_updated: true,
            show_assignee: false,
            show_reporter: false,
            show_milestone_name: false,
            show_tags: false
        };
        Y.Cookie.setSubs(this.cookie_name, expected_config);
        this.list_util = new Y.lp.buglisting_utils.BugListingConfigUtil();
        this.list_util.render();
        var actual_config = this.list_util.get('field_visibility');
        ObjectAssert.areEqual(expected_config, actual_config);
    },

    test_field_visibility_form_reference: function() {
        // The form created from field_visibility defaults is referenced
        // via BugListingConfigUtil.get('form')
        this.list_util = new Y.lp.buglisting_utils.BugListingConfigUtil();
        Assert.isNotUndefined(this.list_util.get('form'));
    },

    test_field_visibility_form_shows_defaults: function() {
        // The form should have a checkbox for every default item,
        // and the checked value should match true or false values.
        this.list_util = new Y.lp.buglisting_utils.BugListingConfigUtil();
        this.list_util.render();
        var expected_names = [
            'show_title',
            'show_id',
            'show_importance',
            'show_status',
            'show_bug_heat',
            'show_bugtarget',
            'show_age',
            'show_last_updated',
            'show_assignee',
            'show_reporter',
            'show_milestone_name',
            'show_tags'
        ];
        var expected_checked = [
            true,
            true,
            true,
            true,
            true,
            true,
            false,
            false,
            false,
            false,
            false,
            false
        ];
        var actual_inputs = this.getActualInputData();
        ArrayAssert.itemsAreSame(expected_names, actual_inputs[0]);
        ArrayAssert.itemsAreSame(expected_checked, actual_inputs[1]);
    },

    test_field_visibility_form_shows_supplied_defaults: function() {
        // The form checkboxes should also match the user supplied
        // config values.
        var field_visibility = {
            show_status: false,
            show_bug_heat: false
        };
        this.list_util = new Y.lp.buglisting_utils.BugListingConfigUtil({
            field_visibility: field_visibility
        });
        this.list_util.render();
        var expected_names = [
            'show_title',
            'show_id',
            'show_importance',
            'show_status',
            'show_bug_heat',
            'show_bugtarget',
            'show_age',
            'show_last_updated',
            'show_assignee',
            'show_reporter',
            'show_milestone_name',
            'show_tags'
        ];
        var expected_checked = [
            true,
            true,
            true,
            false,
            false,
            true,
            false,
            false,
            false,
            false,
            false,
            false
        ];
        var actual_inputs = this.getActualInputData();
        ArrayAssert.itemsAreSame(expected_names, actual_inputs[0]);
        ArrayAssert.itemsAreSame(expected_checked, actual_inputs[1]);
    },

    test_click_icon_reveals_overlay: function() {
        // Clicking the settings icon should reveal the form overlay.
        this.list_util = new Y.lp.buglisting_utils.BugListingConfigUtil();
        this.list_util.render();
        var overlay = this.list_util.get('form').get('boundingBox');
        Assert.isTrue(overlay.hasClass('yui3-lazr-formoverlay-hidden'));
        var config = Y.one('.config');
        config.simulate('click');
        Assert.isFalse(overlay.hasClass('yui3-lazr-formoverlay-hidden'));
    },

    test_field_visibility_form_update_config: function() {
        // Changing elements on the form also updates the field_visibility
        // config values.
        this.list_util = new Y.lp.buglisting_utils.BugListingConfigUtil();
        this.list_util.render();
        var config = Y.one('.config');
        config.simulate('click');
        var show_bugtarget = Y.one('.show_bugtarget');
        var show_bug_heat = Y.one('.show_bug_heat');
        show_bugtarget.simulate('click');
        show_bug_heat.simulate('click');
        var update = Y.one('.update-buglisting');
        update.simulate('click');
        var expected_config = {
            show_title: true,
            show_id: true,
            show_importance: true,
            show_status: true,
            show_bug_heat: false,
            show_bugtarget: false,
            show_age: false,
            show_last_updated: false,
            show_assignee: false,
            show_reporter: false,
            show_milestone_name: false,
            show_tags: false
        };
        var actual_config = this.list_util.get('field_visibility');
        ObjectAssert.areEqual(expected_config, actual_config);
    },

    test_form_update_hides_overlay: function() {
        // Updating the form overlay hides the overlay.
        this.list_util = new Y.lp.buglisting_utils.BugListingConfigUtil();
        this.list_util.render();
        var config = Y.one('.config');
        config.simulate('click');
        var show_bugtarget = Y.one('.show_bugtarget');
        show_bugtarget.simulate('click');
        var update = Y.one('.update-buglisting');
        update.simulate('click');
        var overlay = this.list_util.get('form').get('boundingBox');
        Assert.isTrue(overlay.hasClass('yui3-lazr-formoverlay-hidden'));
    },

    test_update_config_fires_event: function() {
        // A custom event fires when the field_visibility config
        // is updated.
        this.list_util = new Y.lp.buglisting_utils.BugListingConfigUtil();
        this.list_util.render();
        // Setup event handler.
        var event_fired = false;
        Y.on('buglisting-config-util:fields-changed', function(e) {
            event_fired = true;
        });
        // Poke at the page to update the form.
        var config = Y.one('.config');
        config.simulate('click');
        var show_bugtarget = Y.one('.show_bugtarget');
        show_bugtarget.simulate('click');
        var update = Y.one('.update-buglisting');
        update.simulate('click');
        // Confirm the event handler worked.
        Assert.isTrue(event_fired);
    },

    test_update_from_form_updates_cookie: function() {
        // When the form is submitted, a cookie is set to match
        // your preferred field_visibility.
        this.list_util = new Y.lp.buglisting_utils.BugListingConfigUtil();
        this.list_util.render();
        // Now poke at the page to set the cookie.
        var config = Y.one('.config');
        config.simulate('click');
        var show_bugtarget = Y.one('.show_bugtarget');
        show_bugtarget.simulate('click');
        var update = Y.one('.update-buglisting');
        update.simulate('click');
        var expected_config = {
            show_title: true,
            show_id: true,
            show_importance: true,
            show_status: true,
            show_bug_heat: true,
            show_bugtarget: false,
            show_age: false,
            show_last_updated: false,
            show_assignee: false,
            show_reporter: false,
            show_milestone_name: false,
            show_tags: false
        };
        var expected_cookie = Y.Cookie._createCookieHashString(
            expected_config);
        var actual_cookie = Y.Cookie.get(this.cookie_name);
        Assert.areEqual(expected_cookie, actual_cookie);
    },

    test_fields_visibility_form_reset: function() {
        // Clicking "reset to defaults" on the form returns
        // field_visibility to its default values.
        var field_visibility = {
            show_bugtarget: true,
            show_bug_heat: false
        };
        this.list_util = new Y.lp.buglisting_utils.BugListingConfigUtil({
            field_visibility: field_visibility
        });
        this.list_util.render();
        // Setup event handler.
        var event_fired = false;
        Y.on('buglisting-config-util:fields-changed', function(e) {
            event_fired = true;
            // Confirm that field_visibility is now the same as the defaults.
            var defaults = this.list_util.field_visibility_defaults;
            var fields = this.list_util.get('field_visibility');
            ObjectAssert.areEqual(defaults, fields);
        }, this);
        // Poke at the page to reset the form.
        var config = Y.one('.config');
        config.simulate('click');
        Y.one('.reset-buglisting').simulate('click');
        Assert.isTrue(event_fired);
    },

    test_fields_visibility_form_reset_hides_overlay: function() {
        // Reseting to defaults should hide the form overlay.
        var field_visibility = {
            show_bugtarget: true,
            show_bug_heat: false
        };
        this.list_util = new Y.lp.buglisting_utils.BugListingConfigUtil({
            field_visibility: field_visibility
        });
        this.list_util.render();
        // Poke at the form to reset defaults.
        var config = Y.one('.config');
        config.simulate('click');
        Y.one('.reset-buglisting').simulate('click');
        var overlay = this.list_util.get('form').get('boundingBox');
        Assert.isTrue(overlay.hasClass('yui3-lazr-formoverlay-hidden'));
    },

    test_fields_visibility_form_reset_updates_form: function() {
        // Reseting to defaults should reset the form inputs, too.
        var field_visibility = {
            show_bugtarget: false,
            show_bug_heat: false
        };
        this.list_util = new Y.lp.buglisting_utils.BugListingConfigUtil({
            field_visibility: field_visibility
        });
        this.list_util.render();
        var expected_names = [
            'show_title',
            'show_id',
            'show_importance',
            'show_status',
            'show_bug_heat',
            'show_bugtarget',
            'show_age',
            'show_last_updated',
            'show_assignee',
            'show_reporter',
            'show_milestone_name',
            'show_tags'
        ];
        var expected_checked = [
            true,
            true,
            true,
            true,
            true,
            true,
            false,
            false,
            false,
            false,
            false,
            false
        ];
        // Poke at the form to reset defaults.
        var config = Y.one('.config');
        config.simulate('click');
        Y.one('.reset-buglisting').simulate('click');
        var actual_inputs = this.getActualInputData();
        ArrayAssert.itemsAreSame(expected_names, actual_inputs[0]);
        ArrayAssert.itemsAreSame(expected_checked, actual_inputs[1]);
    }

}));

buglisting_utils.suite = suite;

}, '0.1', {'requires': [
    'test', 'node-event-simulate', 'cookie', 'lp.buglisting_utils']});
