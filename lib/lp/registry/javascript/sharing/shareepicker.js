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
    // Override for testing
    anim_duration: {
        value: 1
    }
};


Y.extend(ShareePicker, Y.lazr.picker.Picker, {
    initializer: function(config) {
        ShareePicker.superclass.initializer.apply(this, arguments);
        var information_types = [];
        if (config !== undefined) {
            if (config.information_types !== undefined) {
                information_types = config.information_types;
            }
        }
        this.set('information_types', information_types);
        var self = this;
        this.subscribe('save', function (e) {
            e.preventDefault();
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
        var title = Y.Lang.substitute('Select sharing policy for {name}',
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
                    e.preventDefault();
                    self._display_step_one();
                });
            }
            // Wire up the next (ie submit) links.
            step_two_content.all('.next').on('click', function(e) {
                e.preventDefault();
                // Only submit if at least one info type is selected.
                if (!self._all_info_choices_unticked(step_two_content)) {
                    self.fire('save', data, 2);
                }
            });
            step_two_content.one('div.step-links')
                .insert(self._make_policy_selector(), 'before');
            step_one_content.insert(step_two_content, 'after');
            step_two_content.all('input[name=field.visibility]')
                    .on('click', function(e) {
                self._disable_select_if_all_info_choices_unticked(
                    step_two_content);
            });
        }
        // If we have been given values for the information_type data, ensure
        // the relevant checkboxes are ticked.
        if (Y.Lang.isArray(data.information_types)) {
            Y.Array.each(data.information_types, function(info_type) {
                var cb = step_two_content.one(
                    'input[name=field.visibility]' +
                    '[value="'+info_type+'"]');
                if (Y.Lang.isValue(cb)) {
                    cb.set('checked', true);
                }
            });
        }
        this._disable_select_if_all_info_choices_unticked(step_two_content);
        this._fade_in(step_two_content, step_one_content);
    },

    /**
     * Are all the info type checkboxes unticked?
     * @param content
     * @return {Boolean}
     * @private
     */
    _all_info_choices_unticked: function(content) {
        var all_unticked = true;
        content.all('input[name=field.visibility]')
                .each(function(info_node) {
            all_unticked &= !info_node.get('checked');
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
        // Determine the chosen information type. data already contains the
        // selected person due to the base picker behaviour.
        var contentBox = this.get('contentBox');
        var selected_info_types = [];
        contentBox.all('input[name=field.visibility]')
            .each(function(node) {
                if (node.get('checked')) {
                    selected_info_types.push(node.get('value'));
                }
            });
        data.information_types = selected_info_types;
        // Publish the result with step_nr 0 to indicate we have finished.
        this.fire('save', data, 0);
    },

    _make_policy_selector: function() {
        // The policy selector is a set of radio buttons.
        var html = Y.lp.mustache.to_html([
            '<div class="selection-choices">',
            '<table class="radio-button-widget"><tbody>',
            '{{#policies}}',
            '    <tr>',
            '      <td rowspan="2"><input type="checkbox"',
            '        value="{{title}}"',
            '        name="field.visibility"',
            '        id="field.visibility.{{index}}"',
            '        class="checkboxType">',
            '      </td>',
            '      <td><label for="field.visibility.{{index}}">',
            '        <span class="accessPolicy{{value}}">{{title}}',
            '        </span></label>',
            '      </td>',
            '    </tr>',
            '    <tr>',
            '      <td class="formHelp">',
            '     {{description}}',
            '      </td>',
            '    </tr>',
            '{{/policies}}',
            '</tbody></table></div>'
        ].join(''), {
            policies: this.get('information_types')
        });
        return Y.Node.create(html);
    },

    _syncProgressUI: function() {
        // The base picker behaviour is to set the progress bar to 100% once
        // the search results are displayed. We want to control the progress
        // bar as the user steps through the picker screens.
    },

    _clear: function() {
        var contentBox = this.get('contentBox');
        var first_button = contentBox.one('input[id=field.visibility.0]');
        if (first_button !== null) {
            first_button.set('checked', 'checked');
        }
        this.constructor.superclass._clear.call(this);
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
                    information_types: config.selected_permissions,
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

