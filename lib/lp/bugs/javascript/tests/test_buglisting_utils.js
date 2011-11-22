/* Copyright (c) 2011, Canonical Ltd. All rights reserved. */

YUI.add('lp.buglisting_utils.test', function(Y) {

var buglisting_utils = Y.namespace('lp.buglisting_utils.test');

var suite = new Y.Test.Suite('BugListingConfigUtil Tests');

var Assert = Y.Assert;
var ArrayAssert = Y.ArrayAssert;
var ObjectAssert = Y.ObjectAssert;

suite.add(new Y.Test.Case({

    name: 'buglisting_display_utils_tests',

    setUp: function() {
        // Default values for model config.
        this.defaults = {
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
        };
    },

    tearDown: function() {
        if (Y.Lang.isValue(this.list_util)) {
            this.list_util.destroy();
        }
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

    test_bug_listing_util_extends_base_util: function() {
        // BugListingConfigUtil extends from BaseConfigUtil.
        this.list_util = new Y.lp.buglisting_utils.BugListingConfigUtil();
        Assert.isInstanceOf(Y.lp.configutils.BaseConfigUtil, this.list_util);
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
        this.list_util.get('model').set(
            'field_visibility_defaults', attempted_defaults);
        ObjectAssert.areEqual(
            this.list_util.get('field_visibility_defaults'),
            this.defaults.field_visibility_defaults);
    },

    test_field_visibility_form_reference: function() {
        // The form created from field_visibility defaults is referenced
        // via BugListingConfigUtil.get('form')
        this.list_util = new Y.lp.buglisting_utils.BugListingConfigUtil();
        Assert.isNotUndefined(this.list_util.get('form'));
    },

    test_field_visibility_form_shows_initial: function() {
        // The form should have a checkbox for every field_visibility item,
        // and the checked value should match true or false values.
        this.list_util = new Y.lp.buglisting_utils.BugListingConfigUtil(
            this.defaults);
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
            false,
            false,
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
        var field_visibility = Y.merge(
            this.defaults.field_visibility_defaults, {
            show_status: false,
            show_bug_heat: false
        });
        this.list_util = new Y.lp.buglisting_utils.BugListingConfigUtil({
            field_visibility: field_visibility,
            field_visibility_defaults: this.defaults.field_visibility_defaults
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
            false,
        ];
        var actual_inputs = this.getActualInputData();
        ArrayAssert.itemsAreSame(expected_names, actual_inputs[0]);
        ArrayAssert.itemsAreSame(expected_checked, actual_inputs[1]);
    },

    test_click_icon_reveals_overlay: function() {
        // Clicking the settings icon should reveal the form overlay.
        this.list_util = new Y.lp.buglisting_utils.BugListingConfigUtil(
            this.defaults);
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
        this.list_util = new Y.lp.buglisting_utils.BugListingConfigUtil(
            this.defaults);
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
            show_id: false,
            show_importance: false,
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
        var model = this.list_util.get('model');
        var actual_config = model.get_field_visibility();
        ObjectAssert.areEqual(expected_config, actual_config);
    },

    test_form_update_hides_overlay: function() {
        // Updating the form overlay hides the overlay.
        this.list_util = new Y.lp.buglisting_utils.BugListingConfigUtil(
            this.defaults);
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

    test_fields_visibility_form_reset: function() {
        // Clicking "reset to defaults" on the form returns
        // field_visibility to its default values.
        var field_visibility = {
            show_bugtarget: true,
            show_bug_heat: false
        };
        this.list_util = new Y.lp.buglisting_utils.BugListingConfigUtil({
            field_visibility: field_visibility,
            field_visibility_defaults: this.defaults.field_visibility_defaults
        });
        this.list_util.render();
        // Poke at the page to reset the form.
        var config = Y.one('.config');
        config.simulate('click');
        Y.one('.reset-buglisting').simulate('click');
        var model = this.list_util.get('model');
        var defaults = model.get('field_visibility_defaults');
        var fields = model.get_field_visibility();
        ObjectAssert.areEqual(defaults, fields);
    },

    test_fields_visibility_form_reset_hides_overlay: function() {
        // Reseting to defaults should hide the form overlay.
        var field_visibility = {
            show_bugtarget: true,
            show_bug_heat: false
        };
        this.list_util = new Y.lp.buglisting_utils.BugListingConfigUtil({
            field_visibility: field_visibility,
            field_visibility_defaults: this.defaults.field_visibility_defaults
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
        var field_visibility = Y.merge(
            this.defaults.field_visibility_defaults, {
            show_bugtarget: false,
            show_bug_heat: false
        });
        this.list_util = new Y.lp.buglisting_utils.BugListingConfigUtil({
            field_visibility: field_visibility,
            field_visibility_defaults: this.defaults.field_visibility_defaults
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
    'test', 'node-event-simulate', 'lp.buglisting_utils']});
