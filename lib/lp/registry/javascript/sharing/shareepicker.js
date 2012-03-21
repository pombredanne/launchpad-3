/* Copyright 2012 Canonical Ltd.  This software is licensed under the
 * GNU Affero General Public License version 3 (see the file LICENSE).
 *
 * Disclosure infrastructure.
 *
 * @module lp.registry.sharing
 */

YUI.add('lp.registry.sharing.shareepicker', function(Y) {

var namespace = Y.namespace('lp.registry.sharing.shareepicker');

var ShareePicker;
ShareePicker = function() {
    ShareePicker.superclass.constructor.apply(this, arguments);

};

ShareePicker.ATTRS = {
   /**
    * The available information types.
    *
    * @attribute information_types
    * @type Object
    * @default []
    */
    information_types: {
        value: []
    },
    sharing_permissions: {
        value: []
    },
    // Override for testing
    anim_duration: {
        value: 1
    }
};


Y.extend(ShareePicker, Y.lazr.picker.Picker, {
    initializer: function(config) {
        ShareePicker.superclass.initializer.apply(this, arguments);
        var information_types = [];
        var sharing_permissions = [];
        if (config !== undefined) {
            if (config.information_types !== undefined) {
                information_types = config.information_types;
            }
            if (config.sharing_permissions !== undefined) {
                sharing_permissions = config.sharing_permissions;
            }
        }
        this.set('information_types', information_types);
        this.set('sharing_permissions', sharing_permissions);
        var self = this;
        this.subscribe('save', function (e) {
            e.halt();
            // The step number indicates which picker step has just fired.
            var step_nr = e.details[1];
            if (!Y.Lang.isNumber(step_nr)) {
                step_nr = 1;
            }
            var data = e.details[Y.lazr.picker.Picker.SAVE_RESULT];
            switch(step_nr) {
                case 1:
                    self._display_step_two(data);
                    break;
                case 2:
                    self._publish_result(data);
                    break;
                default:
                    return;
            }
        });
    },

    _fade_in: function(content_node, old_content) {
        content_node.removeClass('unseen');
        if (old_content === null) {
            return;
        }
        old_content.addClass('unseen');
        var anim_duration = this.get('anim_duration');
        if (anim_duration === 0) {
            return;
        }
        content_node.addClass('transparent');
        content_node.setStyle('opacity', 0);
        var fade_in = new Y.Anim({
            node: content_node,
            to: {opacity: 1},
            duration: anim_duration
        });
        fade_in.run();
    },

    _display_step_one: function() {
        this.set(
            'steptitle',
            'Search for user or exclusive team with whom to share');
        this.set('progress', 50);
        var contentBox = this.get('contentBox');
        var step_one_content = contentBox.one('.yui3-widget-bd');
        var step_two_content = contentBox.one('.picker-content-two');
        this._fade_in(step_one_content, step_two_content);
    },

    _display_step_two: function(data) {
        var title = Y.Lang.substitute('Select sharing policies for {name}',
            {name: data.title});
        this.set('steptitle', title);
        this.set('progress', 75);
        var contentBox = this.get('contentBox');
        var step_one_content = contentBox.one('.yui3-widget-bd');
        var step_two_content = contentBox.one('.picker-content-two');
        if (step_two_content === null) {
            var step_two_html = [
                '<div class="picker-content-two transparent">',
                '<div class="step-links">',
                '<a class="prev js-action" href="#">Back</a>',
                '<button class="next lazr-pos lazr-btn"></button>',
                '<a class="next js-action" href="#">Select</a>',
                '</div></div>'
                ].join(' ');
            step_two_content = Y.Node.create(step_two_html);
            var self = this;
            // Remove the back link if required.
            if (Y.Lang.isBoolean(data.back_enabled)
                    && !data.back_enabled ) {
                step_two_content.one('a.prev').remove(true);
            } else {
                step_two_content.one('a.prev').on('click', function(e) {
                    e.halt();
                    self._display_step_one();
                });
            }
            // Wire up the next (ie submit) links.
            step_two_content.all('.next').on('click', function(e) {
                e.halt();
                // Only submit if at least one info type is selected.
                if (!self._all_info_choices_unticked(step_two_content)) {
                    self.fire('save', data, 2);
                }
            });
            var allowed_permissions = ['ALL', 'NOTHING'];
            if (Y.Lang.isValue(data.allowed_permissions)) {
                allowed_permissions = data.allowed_permissions;
            }
            var sharing_permissions = [];
            Y.Array.each(this.get('sharing_permissions'),
                    function(permission) {
                if (Y.Array.indexOf(
                        allowed_permissions, permission.value) >=0) {
                    sharing_permissions.push(permission);
                }
            });
            var policy_selector = self._make_policy_selector(
                sharing_permissions);
            step_two_content.one('div.step-links')
                .insert(policy_selector, 'before');
            step_one_content.insert(step_two_content, 'after');
            step_two_content.all('input[name^=field.permission]')
                    .on('click', function(e) {
                self._disable_select_if_all_info_choices_unticked(
                    step_two_content);
            });
        }
        // Initially set radio button to Nothing.
        step_two_content.all('input[name^=field.permission][value=NOTHING]')
                .each(function(radio_button) {
            radio_button.set('checked', true);
        });
        // Ensure the correct radio buttons are ticked according to the
        // sharee_permissions.
        if (Y.Lang.isObject(data.sharee_permissions)) {
            Y.each(data.sharee_permissions, function(perm, type) {
                var cb = step_two_content.one(
                    'input[name=field.permission.'+type+']' +
                    '[value="' + perm + '"]');
                if (Y.Lang.isValue(cb)) {
                    cb.set('checked', true);
                }
            });
        }
        this._disable_select_if_all_info_choices_unticked(step_two_content);
        this._fade_in(step_two_content, step_one_content);
    },

    /**
     * Are all the radio buttons set to Nothing?
     * @param content
     * @return {Boolean}
     * @private
     */
    _all_info_choices_unticked: function(content) {
        var all_unticked = true;
        content.all('input[name^=field.permission]')
                .each(function(info_node) {
            if (info_node.get('value') !== 'NOTHING') {
                all_unticked &= !info_node.get('checked');
            }
        });
        return all_unticked;
    },

    /**
     * Disable the select links if no info type checkboxes are ticked.
     * @param content
     * @private
     */
    _disable_select_if_all_info_choices_unticked: function(content) {
        var disable_links = this._all_info_choices_unticked(content);
        content.all('.next').each(function(node) {
            if (disable_links) {
                node.addClass('invalid-link');
            } else {
                node.removeClass('invalid-link');
            }
        });
    },

    _publish_result: function(data) {
        // Determine the selected permisios. data already contains the
        // selected person due to the base picker behaviour.
        var contentBox = this.get('contentBox');
        var selected_permissions = {};
        Y.Array.each(this.get('information_types'), function(info_type) {
            contentBox.all('input[name=field.permission.'+info_type.value+']')
                .each(function(node) {
                    if (node.get('checked')) {
                        selected_permissions[info_type.value]
                            = node.get('value');
                    }
                });
        });
        data.selected_permissions = selected_permissions;
        // Publish the result with step_nr 0 to indicate we have finished.
        this.fire('save', data, 0);
    },

    _sharing_permission_template: function() {
        return [
            '<table class="radio-button-widget"><tbody>',
            '{{#permissions}}',
            '<tr>',
            '      <input type="radio"',
            '        value="{{value}}"',
            '        name="field.permission.{{info_type}}"',
            '        id="field.permission.{{info_type}}.{{index}}"',
            '        class="radioType">',
            '    <label for="field.permission.{{info_type}}"',
            '        title="{{description}}">',
            '        {{title}}',
            '    </label>',
            '</tr>',
            '{{/permissions}}',
            '</tbody></table>'
        ].join('');
    },

    _make_policy_selector: function(allowed_permissions) {
        // The policy selector is a set of radio buttons.
        var sharing_permissions_template = this._sharing_permission_template();
        var html = Y.lp.mustache.to_html([
            '<div class="selection-choices">',
            '<table><tbody>',
            '{{#policies}}',
            '<tr>',
            '      <td><strong>',
            '        <span class="accessPolicy{{value}}">{{title}}',
            '        </span>',
            '      </strong></td>',
            '</tr>',
            '<tr>',
            '    <td>',
            '    {{#sharing_permissions}} {{/sharing_permissions}}',
            '    </td>',
            '</tr>',
            '<tr>',
            '    <td class="formHelp">',
            '        {{description}}',
            '    </td>',
            '</tr>',
            '{{/policies}}',
            '</tbody></table></div>'
        ].join(''), {
            policies: this.get('information_types'),
            sharing_permissions: function() {
                return function(text, render) {
                    return Y.lp.mustache.to_html(sharing_permissions_template, {
                        permissions: allowed_permissions,
                        info_type: render('{{value}}')
                    });
                };
            }
        });
        return Y.Node.create(html);
    },

    _syncProgressUI: function() {
        // The base picker behaviour is to set the progress bar to 100% once
        // the search results are displayed. We want to control the progress
        // bar as the user steps through the picker screens.
    },

    hide: function() {
        this.get('boundingBox').setStyle('display', 'none');
        var contentBox = this.get('contentBox');
        var step_two_content = contentBox.one('.picker-content-two');
        if (step_two_content !== null) {
            step_two_content.remove(true);
        }
        this.constructor.superclass.hide.call(this);
    },

    /**
     * Show the picker. We can pass in config which allows us to tell the
     * picker to show a screen other than the first, and whether to disable
     * the back link.
     * @param state_config
     */
    show: function(state_config) {
        var config = {
            first_step: 1
        };
        if (Y.Lang.isValue(state_config)) {
            config = Y.merge(config, state_config);
        }
        switch (config.first_step) {
            case 2:
                var data = {
                    title: config.sharee.person_name,
                    api_uri: config.sharee.person_uri,
                    sharee_permissions: config.sharee_permissions,
                    allowed_permissions: config.allowed_permissions,
                    back_enabled: false
                };
                this._display_step_two(data);
                break;
            default:
                this._display_step_one();
                break;
        }
        this.get('boundingBox').setStyle('display', 'block');
        this.constructor.superclass.show.call(this);
    }

});

ShareePicker.NAME = 'sharee_picker';
namespace.ShareePicker = ShareePicker;

}, "0.1", { "requires": ['node', 'lp.mustache', 'lazr.picker'] });

