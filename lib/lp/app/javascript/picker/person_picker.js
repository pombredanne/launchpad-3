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
        if (this.get('show_create_team')) {
            // We need to provide the 'New team' link.
            // There could be several pickers and we only want to make the XHR
            // call to get the form once. So first one gets to do the call and
            // subsequent ones register the to be notified of the result.
            this.team_form_node = Y.Node.create(this._new_team_template());
            this.form_namespace = Y.namespace('lp.app.picker.teamform');
            var form_callbacks = this.form_namespace.form_callbacks;
            var perform_load = false;
            if (!Y.Lang.isArray(form_callbacks)) {
                perform_load = true;
                form_callbacks = [];
                this.form_namespace.form_callbacks = form_callbacks;
            }
            form_callbacks.push({
                picker: this,
                callback: this._render_new_team_form});
            this._load_new_team_form(perform_load);
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

    _load_new_team_form: function (perform_load) {
        // Load the new team form from the model using an XHR call.
        // If perform_load is true, this is the first invocation of this method
        // across all pickers so we do the XHR call and send the result to all
        // registered pickers.
        // If perform_load is false, another picker is making the XNR call and
        // all we want to do is receive and render the preloaded_team_form.
        // We first check though that the result hasn't arrived already.
        var preloaded_team_form = this.form_namespace.team_form;
        if (Y.Lang.isValue(preloaded_team_form)) {
            this._render_new_team_form(preloaded_team_form, true);
            return;
        }
        if (!perform_load) {
            return;
        }

        function on_success(id, response, picker) {
            Y.Array.each(picker.form_namespace.form_callbacks,
                function(callback_info) {
                Y.bind(
                    callback_info.callback, callback_info.picker,
                    response.responseText, true)();
            });
            picker.form_namespace.team_form = response.responseText;
        }
        function on_failure(id, response, picker) {
            Y.Array.each(picker.form_namespace.form_callbacks,
                function(callback_info) {
                Y.bind(
                    callback_info.callback, callback_info.picker,
                    'Sorry, an error occurred while loading the form.',
                    false)();
            });
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
        // Poke the actual team form into the DOM and wire up the save and
        // cancel buttons.
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
