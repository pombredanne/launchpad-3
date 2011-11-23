/* Copyright (c) 2011, Canonical Ltd. All rights reserved. */

YUI().add('lp.buglisting_utils', function(Y) {
    /**
     * A utility for configuring the display of bug listings.
     *
     * The purpose of this widget is be a mechanism for turning
     * fields on and off in a bug listing display.  It extends
     * from BaseConfigUtil, which provides the clickable settings
     * icon.  When the icon is clicked, a form overlay opens with
     * various checkboxes for turning fields on and off.
     *
     * This doesn't actually change the display, though.  It fires
     * an event that the buglisting navigator will hook into to update
     * the list's display.
     *
     * @module lp.buglisting_utils
     */

    // Constants.
    var FORM = 'form',
        FIELD_VISIBILITY = 'field_visibility';



    /**
     * BugListingConfigUtil is the main object used to manipulate
     * a bug listing's display.
     *
     * @class BugListingConfigUtil
     * @extends Y.lp.configutils.BaseConfigUtil
     * @constructor
     */
    function BugListingConfigUtil() {
        BugListingConfigUtil.superclass.constructor.apply(this, arguments);
    }

    BugListingConfigUtil.NAME = 'buglisting-config-util';

    /**
     * Object to reference display names for field_visibility
     * form inputs.
     */
    BugListingConfigUtil.field_display_names = {
        show_title: 'Bug title',
        show_id: 'Bug number',
        show_importance: 'Importance',
        show_status: 'Status',
        show_bug_heat: 'Bug heat',
        show_bugtarget: 'Package/Project/Series name',
        show_age: 'Bug age',
        show_last_updated: 'Date bug last updated',
        show_assignee: 'Assignee',
        show_reporter: 'Reporter',
        show_milestone_name: 'Milestone',
        show_tags: 'Bug tags'
    };

    BugListingConfigUtil.ATTRS = {

        /**
         * The cookie name as set by the view.
         *
         * We get this value from the LP cache.
         *
         * @attribute cookie_name
         * @type String
         */
        cookie_name: {
            valueFn: function() {
                if (
                    Y.Lang.isValue(window.LP) &&
                    Y.Lang.isValue(LP.cache.cbl_cookie_name)) {
                    return LP.cache.cbl_cookie_name;
                } else {
                    return '';
                }
            }
        },

        /**
         * A reference to the form overlay used in the overlay.
         *
         * @attribute form
         * @type Y.lazr.FormOverlay
         * @default null
         */
        form: {
            value: null
        },
        model: {
            value: null
        }
    };

    BugListingConfigUtil.INPUT_TEMPLATE = [
        '<input type="checkbox" class="{name}" name="{name}" ',
        'value="{display_name}" {checked}> {display_name}<br />'].join('');

    Y.extend(BugListingConfigUtil, Y.lp.configutils.BaseConfigUtil, {

        initializer: function(config){
            if (config === undefined){
                config = {};
            }
            if (Y.Lang.isNull(this.get('model'))){
                this.set('model',
                    new Y.lp.bugs.buglisting.BugListingModel(config));
            }
        },

        /**
         * Hook into the destroy lifecyle to ensure the form
         * overlay is destroyed.
         *
         * @method destructor
         */
        destructor: function() {
            if (Y.Lang.isValue(this.get(FORM))) {
                var form = this.get(FORM);
                this.set(FORM, null);
                form.destroy();
            }
        },

        /**
         * Build the input nodes used on the form overlay.
         *
         * @method getFormInputs
         */
        getFormInputs: function() {
            var fields = this.get('model').get_field_visibility();
            var display_names = this.constructor.field_display_names;
            var nodes = [];
            var item,
                name,
                display_name,
                checked,
                input_html,
                input_node;
            for (item in fields) {
                if (fields.hasOwnProperty(item)) {
                    name = item;
                    display_name = display_names[item];
                    if (fields[item] === true) {
                        checked = 'checked';
                    } else {
                        checked = '';
                    }
                    input_html = Y.Lang.substitute(
                        this.constructor.INPUT_TEMPLATE,
                        {name: name, display_name: display_name,
                        checked: checked});
                    input_node = Y.Node.create(input_html);
                    nodes.push(input_node);
                }
            }
            return new Y.NodeList(nodes);
        },

        /**
         * Build the reset link for the form.
         *
         * Also, provide a click handler to reset the fields config.
         *
         * @method getResetLink
         */
        getResetLink: function() {
            var link = Y.Node.create('<a></a>');
            link.addClass('js-action');
            link.addClass('reset-buglisting');
            link.setContent('Reset to default');
            link.on('click', function(e) {
                var model = this.get('model');
                var defaults = model.get('field_visibility_defaults');
                this.updateFieldVisibilty(defaults, true);
                this.setCookie();
            }, this);
            return link;
        },

        /**
         * Build the form content for form overlay.
         *
         * @method buildFormContent
         */
        buildFormContent: function() {
            var div = Y.Node.create(
                '<div></div>').addClass('buglisting-opts');
            var inputs = this.getFormInputs();
            div.append(inputs);
            var link = this.getResetLink();
            div.append(link);
            return div;
        },

        /**
         * Helper method for updating field_visibility.
         *
         * @method updateFieldVisibilty
         */
        updateFieldVisibilty: function(fields, destroy_form) {
            this.get('model').set_field_visibility(fields);
            var form = this.get(FORM);
            if (Y.Lang.isValue(form)) {
                form.hide();
            }
            // Destroy the form and rebuild it.
            if (destroy_form === true) {
                this.get(FORM).hide();
                this._extraRenderUI();
            }
        },

        /**
         * Process the data from the form overlay submit.
         *
         * data is an object whose members are the checked
         * input elements from the form.  data has the same members
         * as field_visibility, so if the key is in data it should
         * be set to true in field_visibility.
         *
         * @method handleOverlaySubmit
         */
        handleOverlaySubmit: function(data) {
            var fields = this.get('model').get_field_visibility();
            var member;
            for (member in fields) {
                if (fields.hasOwnProperty(member)) {
                    if (Y.Lang.isValue(data[member])) {
                        // If this field exists in data, set it true.
                        // in field_visibility.
                        fields[member] = true;
                    } else {
                        // Otherwise, set the member to false in
                        // field_visibility.
                        fields[member] = false;
                    }
                }
            }
            this.updateFieldVisibilty(fields);
            this.setCookie(fields);
        },

        /**
         * Update field_visibility based on fields stored
         * in cookies.  This is used as a light-weight
         * page to page persistence mechanism.
         *
         * @method updateFromCookie
         */
        updateFromCookie: function() {
            var cookie_name = this.get('cookie_name');
            var cookie_fields = Y.Cookie.getSubs(cookie_name);
            if (Y.Lang.isValue(cookie_fields)) {
                // We get true/false back as strings from Y.Cookie,
                // so we have to convert them to booleans.
                Y.each(cookie_fields, function(val, key, obj) {
                    if (val === 'true') {
                        val = true;
                    } else {
                        val = false;
                    }
                    obj[key] = val;
                });
                this.updateFieldVisibilty(cookie_fields);
            }
        },

        /**
         * Set the given value for the buglisting config cookie.
         * If config is not specified, the cookie will be cleared.
         *
         * @method setCookie
         */
        setCookie: function(config) {
            var cookie_name = this.get('cookie_name');
            if (Y.Lang.isValue(config)) {
                Y.Cookie.setSubs(cookie_name, config, {
                    path: '/',
                    expires: new Date('January 19, 2038')});
            } else {
                Y.Cookie.remove(cookie_name);
            }
        },

        /**
         * Hook in _extraRenderUI provided by BaseConfigUtil
         * to add a form overlay to the widget.
         *
         * @method _extraRenderUI
         */
        _extraRenderUI: function() {
            this.updateFromCookie();
            var form_content = this.buildFormContent();
            var on_submit_callback = Y.bind(this.handleOverlaySubmit, this);
            util_overlay = new Y.lazr.FormOverlay({
                align: 'left',
                headerContent: '<h2>Visible information</h2>',
                centered: true,
                form_content: form_content,
                form_submit_button: Y.Node.create(
                    '<input type="submit" value="Update" ' +
                    'class="update-buglisting" />'
                ),
                form_cancel_button: Y.Node.create(
                    '<button type="button" name="field.actions.cancel" ' +
                    'class="hidden" >Cancel</button>'
                ),
                form_submit_callback: on_submit_callback
            });
            util_overlay.get(
                'boundingBox').addClass(this.getClassName('overlay'));
            this.set(FORM, util_overlay);
            util_overlay.render();
            util_overlay.hide();
        },

        /**
         * Hook into _handleClick provided by BaseConfigUtil
         * to show overlay when the settings cog icon is clicked.
         *
         * @method _handleClick
         */
        _handleClick: function() {
            var form = this.get(FORM);
            form.show();
        }

    });

    var buglisting_utils = Y.namespace('lp.buglisting_utils');
    buglisting_utils.BugListingConfigUtil = BugListingConfigUtil;

}, '0.1', {'requires': [
    'cookie', 'history', 'lp.configutils', 'lazr.formoverlay',
    'lp.bugs.buglisting'
    ]});
