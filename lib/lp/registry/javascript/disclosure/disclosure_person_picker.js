/* Copyright 2012 Canonical Ltd.  This software is licensed under the
 * GNU Affero General Public License version 3 (see the file LICENSE).
 *
 * Disclosure infrastructure.
 *
 * @module lp.registry.disclosure
 */

YUI.add('lp.registry.disclosure', function(Y) {

var namespace = Y.namespace('lp.registry.disclosure');

var DisclosurePicker;
DisclosurePicker = function() {
    DisclosurePicker.superclass.constructor.apply(this, arguments);

};

DisclosurePicker.ATTRS = {
   /**
    * The value, in percentage, of the progress bar.
    *
    * @attribute access_policies
    * @type Object
    * @default []
    */
    access_policies: {
        value: []
    }
};


Y.extend(DisclosurePicker, Y.lazr.picker.Picker, {
    initializer: function(config) {
        DisclosurePicker.superclass.initializer.apply(this, arguments);
        var access_policies = [];
        if (config !== undefined) {
            if (config.access_policies !== undefined) {
                access_policies = config.access_policies;
            }
        }
        this.set('access_policies', access_policies);
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

    _display_step_one: function() {
        this.set('steptitle', 'Search for someone with whom to share');
        this.set('progress', 50);
        var contentBox = this.get('contentBox');
        var step_two_content = contentBox.one('.picker-content-two');
        if (step_two_content !== null) {
            step_two_content.addClass('unseen');
        }
        var step_one_content = contentBox.one('.yui3-widget-bd');
        step_one_content.removeClass('unseen');
    },

    _display_step_two: function(data) {
        var title = Y.Lang.substitute('Select access policy for {name}',
            {name: data.title});
        this.set('steptitle', title);
        this.set('progress', 75);
        var contentBox = this.get('contentBox');
        var step_one_content = contentBox.one('.yui3-widget-bd');
        step_one_content.addClass('unseen');
        var step_two_content = contentBox.one('.picker-content-two');
        if (step_two_content === null) {
            var step_two_html = [
                '<div class="picker-content-two">',
                '<div class="step-links">',
                '<a class="prev js-action" href="#">Back</a>',
                '<button class="next lazr-pos lazr-btn"></button>',
                '<a class="next js-action" href="#">Select</a>',
                '</div></div>'
                ].join(' ');
            step_two_content = Y.Node.create(step_two_html);
            var self = this;
            step_two_content.one('a.prev').on('click', function(e) {
                e.preventDefault();
                self._display_step_one();
            });
            step_two_content.all('.next').on('click', function(e) {
                e.preventDefault();
                self.fire('save', data, 2);
                self._display_step_one();
            });
            step_two_content.one('div.step-links')
                .insert(self._make_policy_selector(), 'before');
            step_one_content.insert(step_two_content, 'after');
            contentBox.one('input[id=field.visibility.0]')
                .set('checked', 'checked');
        }
        step_two_content.removeClass('unseen');
    },

    _publish_result: function(data) {
        // Determine the chosen access policy type. data already contains the
        // selected person due to the base picker behaviour.
        var contentBox = this.get('contentBox');
        var selected_access_policy;
        contentBox.all('input[name=field.visibility]')
            .each(function(node) {
                if (node.get('checked')) {
                    selected_access_policy = node.get('value');
                }
            });
        data.access_policy = selected_access_policy;
        // Publish the result with step_nr 0 to indicate we have finished.
        this.fire('save', data, 0);
    },

    _make_policy_selector: function() {
        // The policy selector is a set of radio buttons.
        var html = Y.lp.mustache.to_html([
            '<div style="margin-top: 0.75em">',
            '<table class="radio-button-widget"><tbody>',
            '{{#policies}}',
            '    <tr>',
            '      <td rowspan="2"><input type="radio"',
            '        value="{{value}}"',
            '        name="field.visibility"',
            '        id="field.visibility.{{index}}"',
            '        class="radioType">',
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
            policies: this.get('access_policies')
        });
        return Y.Node.create(html);
    },

    /**
     * Update the progress UI.
     *
     * @method _syncProgressUI
     * @protected
     */
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
        this.constructor.superclass.hide.call(this);
    },

    show: function() {
        this._display_step_one();
        this.get('boundingBox').setStyle('display', 'block');
        this.constructor.superclass.show.call(this);
    }

});

DisclosurePicker.NAME = 'disclosure_picker';
namespace.DisclosurePicker = DisclosurePicker;

}, "0.1", { "requires": ['node', 'lp.mustache', 'lazr.picker'] });

