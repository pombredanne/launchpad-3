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
        if (this.get('show_create_team')) {
            this._load_new_team_form();
        }
    },

    _new_team_template: function() {
        return [
          '<div class="new-team-node">',
          '<div id=new-team-form-placeholder ',
              'class="yui3-overlay-indicator-content">',
              '<img src="/@@/spinner-big/">',
          '</div>',
          '<div class="extra-form-buttons hidden">',
              '<button class="yes_button" type="button"></button>',
              '<button class="no_button" type="button"></button>',
            '</div>',
          '</div>',
          '</div>'].join('');
    },

    hide: function() {
        this.get('boundingBox').setStyle('display', 'none');
        // We want to cancel the new team form is there is one rendered.
        var node = this.get('contentBox').one('.new-team-node');
        if (Y.Lang.isValue(node) && !node.hasClass('hidden')) {
            this.hide_extra_content(node, false);
        }
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

    _cancel_new_team: function() {
        var node = this.get('contentBox').one('.new-team-node');
        this.hide_extra_content(node);
    },

    _save_new_team: function() {
        var node = this.get('contentBox').one('.new-team-node');
        var team_name = Y.Node.getDOMNode(node.one('[id=field.name]')).value;
        var team_display_name =
            Y.Node.getDOMNode(node.one('[id=field.displayname]')).value;
        this.hide_extra_content(node, false);
        // TODO - make back end call to save team
        var value = {
            "api_uri": "/~" + team_name,
            "title": team_display_name,
            "value": team_name,
            "metadata": "team"};
        this.fire('validate', value);
    },

    _load_new_team_form: function () {
        var html = this.get('new_team_template');
        this.team_form_node = Y.Node.create(html);

        function on_success(id, response, picker) {
            picker._render_new_team_form(
                response.responseText, true);
        }
        function on_failure(id, response, picker) {
            picker._render_new_team_form(
                'Sorry, an error occurred while loading the form.',
                false);
        }
        var cfg = {
            on: {success: on_success, failure: on_failure},
            "arguments": this
            };
        var uri = Y.lp.client.get_absolute_uri('people/+newteam/++form++');
        uri = uri.replace('api/devel', '');
        this.get("io_provider").io(uri, cfg);
    },

    _render_new_team_form: function(form_html, show_submit) {
        var self = this;
        this.team_form_node.one('#new-team-form-placeholder')
            .replace(form_html);
        var button_callback = function(e, callback_fn) {
            e.halt();
            if (Y.Lang.isFunction(callback_fn) ) {
                Y.bind(callback_fn, this)();
            }
        };
        var submit_button = this.team_form_node.one(".yes_button");
        if (show_submit) {
                submit_button.set('text', 'Create Team')
                .on('click', button_callback, this, this._save_new_team);
        } else {
            submit_button.addClass('hidden');
        }
        this.team_form_node.one(".no_button")
            .set('text', 'Cancel')
            .on('click', button_callback, this, this._cancel_new_team);
        this.team_form_node.one('.extra-form-buttons')
            .removeClass('hidden');
    },

    show_new_team_form: function() {
        this.show_extra_content(
            this.team_form_node, "Enter new team details");
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
        if (this.get('show_create_team')) {
            new_team_button = Y.Node.create(this._new_team_button_html());
            new_team_button.on('click', this.show_new_team_form, this);
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
        show_create_team: {value: false},
        new_team_template: {value: null},
        new_team_form: {value: null},
      /**
       * The object that provides the io function for doing XHR requests.
       *
       * @attribute io_provider
       * @type object
       * @default Y
       */
      io_provider: {value: Y}
    }
});
}, "0.1", {"requires": [
    "base", "node", "lazr.picker"]});
