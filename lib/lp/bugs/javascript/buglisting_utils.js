/* Copyright (c) 2011, Canonical Ltd. All rights reserved. */

YUI().add('lp.buglisting_utils', function(Y) {
    /**
     * A utiltiy for configuring the display of bug listings.
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
     *
     * XXX: deryck Don't depend on hard-coded defaults.
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
         * A config for field visibility.  This determines which
         * fields are visibile in a bug listing.
         *
         * @attribute field_visibility
         * @type Object
         */
        field_visibility: {
            valueFn: function() {
                return this.get('field_visibility_defaults');
            },
            setter: function(value) {
                var defaults = this.get('field_visibility_defaults');
                return Y.merge(defaults, value);
            }
        },

        /**
         * Defaults from field_visibility which are taken from LP.cache.
         *
         * This utility will error if LP.cache doesn't exist or doesn't
         * have field_visibility defined.
         *
         * @attribute field_visibility_defaults
         * @type Object
         * @default null
         */
        field_visibility_defaults: {
            valueFn: function() {
                if (
                    Y.Lang.isValue(window.LP) &&
                    Y.Lang.isValue(LP.cache.field_visibility)) {
                    return LP.cache.field_visibility;
                } else {
                    var msg = [
                        'LP.cache.field_visibility must be defined ',
                        'when using BugListingConfigUtil.'
                    ].join('');
                    Y.error(msg);
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
        }
    };

    BugListingConfigUtil.INPUT_TEMPLATE = [
        '<input type="checkbox" class="{name}" name="{name}" ',
        'value="{display_name}" {checked}> {display_name}<br />'].join('');

    Y.extend(BugListingConfigUtil, Y.lp.configutils.BaseConfigUtil, {

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
            var fields = this.get(FIELD_VISIBILITY);
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
                var defaults = this.get('field_visibility_defaults');
                this.set(FIELD_VISIBILITY, defaults);
                var form = this.get(FORM);
                form.hide();
                this.destructor();
                this._extraRenderUI();
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
         * Hook up the global events we want to fire.
         *
         * We do these as a global event rather than listening for
         * attribute change events to avoid having to have a reference
         * to the widget in another widget.
         *
         * @method addListeners
         */
        addListeners: function() {
            // Fire a buglisting-config-util:fields-changed event.
            this.after('field_visibilityChange', function() {
                var event_name = this.constructor.NAME + ':fields-changed';
                Y.fire(event_name);
            });
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
            var fields = this.get('field_visibility_defaults');
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
            this.set(FIELD_VISIBILITY, fields);
            this.get(FORM).hide();
        },

        /**
         * Hook in _extraRenderUI provided by BaseConfigUtil
         * to add a form overlay to the widget.
         *
         * @method _extraRenderUI
         */
        _extraRenderUI: function() {
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
            this.addListeners();
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

}, '0.1', {'requires': ['lp.configutils', 'lazr.formoverlay']});
