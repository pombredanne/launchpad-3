/* Copyright 2011 Canonical Ltd.  This software is licensed under the
 * GNU Affero General Public License version 3 (see the file LICENSE).
 *
 * @namespace Y.lazr.person-picker
 * @requires lazr.picker
 */
YUI.add('lazr.person-picker', function(Y) {

var ns = Y.namespace('lazr.picker');
/*
 * Extend the picker into the PersonPicker
 */

ns.PersonPicker = Y.Base.create('picker', Y.lazr.picker.Picker, [], {

    initializer: function(cfg) {
        // If the user isn't logged in, override the show_assign_me value.
        if (!Y.Lang.isValue(LP.links.me)) {
            this.set('show_assign_me_button', false);
        }
        this.set('new_team_template', this._new_team_template());
        this.set('new_team_form', this._new_team_form());
    },

    _new_team_template: function() {
        return [
          '<div class="new-team-node">',
          '<div class="step-on" style="width: 100%;"></div>',
          '<div class="transparent important-notice-popup">',
            '{{> new_team_form}}',
            '<div class="extra-form-buttons">',
              '<button class="yes_button" type="button"></button>',
              '<button class="no_button" type="button"></button>',
            '</div>',
          '</div>',
          '</div>'].join('');
    },

    _new_team_form: function() {
        // TODO - get the form using ++form++
        return [
        "<table id='launchpad-form-widgets' class='form'>",
        "<tbody><tr><td colspan='2'><div>",
        "<label for='field.name'>Name:</label><div>",
        "<input type='text' value='' size='20'",
        "    name='field.name' id='field.name'",
        "    class='lowerCaseText textType'></div>",
        "<p class='formHelp'>",
        "    A short unique name, beginning with a lower-case letter",
        "    or number, and containing only letters, numbers, dots,",
        "    hyphens, or plus signs.</p>",
        "</div></td></tr><tr><td colspan='2'><div>",
        "<label for='field.displayname'>Display Name:</label><div>",
        "<input type='text' value='' size='20'",
        "    name='field.displayname' id='field.displayname'",
        "    class='textType'></div>",
        "<p class='formHelp'>",
        "    This team's name as you would like it displayed",
        "    throughout Launchpad.</p>",
        "</div></td></tr><tr><td colspan='2'><div>",
        "<label for='field.visibility'>Visibility:</label>",
        "<div><div><div class='value'>",
        "<select size='1'",
        "    name='field.visibility' id='field.visibility'>",
        "<option value='PUBLIC' selected='selected'>Public</option>",
        "<option value='PRIVATE'>Private</option></select></div>",
        "</div></div><p class='formHelp'>",
        "    Anyone can see a public team's data. Only team members",
        "    and Launchpad admins can see private team data.",
        "    Private teams cannot become public.</p>",
        "</div></td></tr></tbody></table>"
        ].join('');
    },

    hide: function() {
        this.get('boundingBox').setStyle('display', 'none');
        Y.lazr.picker.Picker.prototype.hide.call(this);
    },

    show: function() {
        this.get('boundingBox').setStyle('display', 'block');
        Y.lazr.picker.Picker.prototype.show.call(this);
    },

    _update_button_text: function() {
        var link_text;
        if (this.get('selected_value_metadata') === 'team') {
            link_text = this.get('remove_team_text');
        } else {
            link_text = this.get('remove_person_text');
        }
        this.remove_button.set('text', link_text);
    },

    _show_hide_buttons: function () {
        var selected_value = this.get('selected_value');
        if (this.remove_button) {
            if (selected_value === null) {
                this.remove_button.addClass('yui3-picker-hidden');
            } else {
                this.remove_button.removeClass('yui3-picker-hidden');
                this._update_button_text();
            }
        }

        if (this.assign_me_button) {
            if (LP.links.me.match('~' + selected_value + "$") ||
                LP.links.me === selected_value) {
                this.assign_me_button.addClass('yui3-picker-hidden');
            } else {
                this.assign_me_button.removeClass('yui3-picker-hidden');
            }
        }
    },

    remove: function () {
        this.hide();
        this.fire('save', {value: null});
    },

    assign_me: function () {
        var name = LP.links.me.replace('/~', '');
        this.fire('save', {
            image: '/@@/person',
            title: 'Me',
            api_uri: LP.links.me,
            value: name
        });
    },

    _cancel_new_team: function(picker) {
        var node = picker.get('contentBox').one('.new-team-node');
        picker.hide_extra_content(node);
    },

    _save_new_team: function(picker) {
        var node = picker.get('contentBox').one('.new-team-node');
        var team_name = Y.Node.getDOMNode(node.one('[id=field.name]')).value;
        var team_display_name =
            Y.Node.getDOMNode(node.one('[id=field.displayname]')).value;
        picker.hide_extra_content(node);
        // TODO - make back end call to save team
        var value = {
            "api_uri": "/~" + team_name,
            "title": team_display_name,
            "value": team_name,
            "metadata": "team"};
        picker.fire('validate', value);
    },

    new_team: function () {
        var partials = {new_team_form: this.get('new_team_form')};
        var html = Y.lp.mustache.to_html(
            this.get('new_team_template'), {}, partials);
        var self = this;
        var button_callback = function(e, callback_fn) {
            e.halt();
            if (Y.Lang.isFunction(callback_fn) ) {
                callback_fn(self);
            }
        };
        var team_form_node = Y.Node.create(html);
        team_form_node.one(".yes_button")
            .set('text', 'Create Team')
            .on('click', function(e) {
                button_callback(e, self._save_new_team);
            });

        team_form_node.one(".no_button")
            .set('text', 'Cancel')
            .on('click', function(e) {
                button_callback(e, self._cancel_new_team);
            });
        this.get('contentBox').one('.yui3-widget-bd')
            .insert(team_form_node, 'before');
        this.show_extra_content(
            team_form_node.one(".important-notice-popup"),
            "Enter new team details");
    },

    _assign_me_button_html: function() {
        return [
            '<a class="yui-picker-assign-me-button bg-image ',
            'js-action" href="javascript:void(0)" ',
            'style="background-image: url(/@@/person); ',
            'padding-right: 1em">',
            this.get('assign_me_text'),
            '</a>'].join('');
    },

    _remove_button_html: function() {
        return [
            '<a class="yui-picker-remove-button bg-image js-action" ',
            'href="javascript:void(0)" ',
            'style="background-image: url(/@@/remove); ',
            'padding-right: 1em">',
            this.get('remove_person_text'),
            '</a>'].join('');
    },

    _new_team_button_html: function() {
        return [
            '<a class="yui-picker-new-team-button sprite add ',
            'js-action" href="javascript:void(0)">',
            'New Team',
            '</a>'].join('');
    },
    renderUI: function() {
        Y.lazr.picker.Picker.prototype.renderUI.apply(this, arguments);
        var extra_buttons = this.get('extra_buttons');
        var remove_button, assign_me_button, new_team_button;

        if (this.get('show_remove_button')) {
            remove_button = Y.Node.create(this._remove_button_html());
            remove_button.on('click', this.remove, this);
            extra_buttons.appendChild(remove_button);
            this.remove_button = remove_button;
        }

        if (this.get('show_assign_me_button')) {
            assign_me_button = Y.Node.create(this._assign_me_button_html());
            assign_me_button.on('click', this.assign_me, this);
            extra_buttons.appendChild(assign_me_button);
            this.assign_me_button = assign_me_button;
        }
        if (this.get('enhanced_picker')) {
            new_team_button = Y.Node.create(this._new_team_button_html());
            new_team_button.on('click', this.new_team, this);
            extra_buttons.appendChild(new_team_button);
        }
        this._search_input.insert(
            extra_buttons, this._search_input.get('parentNode'));
        this._show_hide_buttons();
        this.after("selected_valueChange", function(e) {
            this._show_hide_buttons();
        });
    }
}, {
    ATTRS: {
        extra_buttons: {
            valueFn: function () {
                return Y.Node.create('<div class="extra-form-buttons"/>');
            }
        },
        show_assign_me_button: { value: true },
        show_remove_button: {value: true },
        assign_me_text: {value: 'Pick me'},
        remove_person_text: {value: 'Remove person'},
        remove_team_text: {value: 'Remove team'},
        min_search_chars: {value: 2},
        enhanced_picker: {value: false},
        new_team_template: {value: null},
        new_team_form: {value: null}
    }
});
}, "0.1", {"requires": ["base", "node", "lazr.picker", "lp.mustache"]});
