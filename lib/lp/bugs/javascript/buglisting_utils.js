/* Copyright (c) 2011, Canonical Ltd. All rights reserved. */

YUI().add('lp.buglisting_utils', function(Y) {
    /**
     * blah, blah, blah.
     *
     * @module lp.buglisting_utils
     */
    function BugListingConfigUtil() {
        BugListingConfigUtil.superclass.constructor.apply(this, arguments);
    }

    BugListingConfigUtil.NAME = 'buglistingconfigutil';

    /**
     * Private object to reference defaults for field_visibility.
     */
    _field_visibility_defaults = {
        show_bugtarget: true,
        show_bug_heat: true,
        show_id: true,
        show_importance: true,
        show_status: true,
        show_title: true,
        show_milestone_name: false
    };

    _field_visibility_display_names = {
        show_bugtarget: 'Bug target',
        show_bug_heat: 'Bug heat',
        show_id: 'Bug number',
        show_importance: 'Importance',
        show_status: 'Status',
        show_title: 'Bug title',
        show_milestone_name: 'Milestone name'

    };

    BugListingConfigUtil.ATTRS = {

        /**
         * A list of [key, name] pairs where key is the class name
         * used to select the element in the DOM, and the name is
         * the display name for the item in the widget.
         *
         * @attribute display_keys
         * @type Array
         */
        display_keys: {
            value: [
                ['bugnumber', 'Bug number'],
                ['bugtitle', 'Bug title'],
                ['importance', 'Importance'],
                ['status', 'Status'],
                ['bug-heat-icons', 'Bug heat']
            ]
        },


        /**
         * A config for field visibility.  This determines which
         * fields are visibile in a bug listing.
         *
         * @attribute field_visibility
         * @type Object
         */
        field_visibility: {
            valueFn: function() {
                return _field_visibility_defaults;
            },
            setter: function(value) {
                var defaults = _field_visibility_defaults;
                return Y.merge(defaults, value);
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
        '<input type="checkbox" name="{name}" ',
        'value="{display_name}" {checked}> {display_name}<br />'].join('');

    Y.extend(BugListingConfigUtil, Y.lp.configutils.BaseConfigUtil, {

        /**
         * Hook into the destroy lifecyle to ensure the form
         * overlay is destroyed.
         *
         * @method destructor
         */
        destructor: function() {
            if (Y.Lang.isValue(this.get('form'))) {
                var form = this.get('form');
                this.set('form', null);
                form.destroy();
            }
        },

        /**
         * Build the input nodes used on the form overlay.
         *
         * @method _getFormInputs
         */
        _getFormInputs: function() {
            var div = Y.Node.create(
                '<div></div>').addClass('buglisting-opts');
            var fields = this.get('field_visibility');
            var name,
                display_name,
                checked,
                input_html,
                input_node;
            for (item in fields) {
                if (fields.hasOwnProperty(item)) {
                    name = item;
                    display_name = _field_visibility_display_names[item];
                    if (fields[item] === true) {
                        checked = 'checked';
                    } else {
                        checked = '';
                    }
                }
                input_html = Y.Lang.substitute(
                    this.constructor.INPUT_TEMPLATE,
                    {name: name, display_name: display_name,
                    checked: checked});
                input_node = Y.Node.create(input_html);
                div.appendChild(input_node);
            }
            return div;
        },

        /**
         * Hook in _extraRenderUI provided by BaseConfigUtil
         * to add a form overlay to the widget.
         *
         * @method _extraRenderUI
         */
        _extraRenderUI: function() {
            var inputs = this._getFormInputs();
            util_overlay = new Y.lazr.FormOverlay({
                align: 'left',
                headerContent: '<h2>Items to display</h2>',
                centered: true,
                form_content: inputs,
                form_submit_button: Y.Node.create(
                    '<input type="submit" value="Update" ' +
                    'class="update-buglisting" />'
                ),
                form_cancel_button: Y.Node.create(
                    '<button type="button" name="field.actions.cancel" ' +
                    'class="lazr-neg lazr-btn" >Cancel</button>'
                ),
                form_submit_callback: function() {Y.log('do nothing')}
            });
            this.set('form', util_overlay);
            util_overlay.render();
            util_overlay.hide();
        }
    });

    var buglisting_utils = Y.namespace('lp.buglisting_utils');
    buglisting_utils.BugListingConfigUtil = BugListingConfigUtil;

}, '0.1', {'requires': ['lp.configutils', 'lazr.formoverlay']});
