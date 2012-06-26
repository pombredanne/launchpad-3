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
            this.new_team_form = Y.Node.create('<form/>');
            this.new_team_form.appendChild(this._new_team_template());
            this.team_form_error_handler =
                new Y.lp.client.FormErrorHandler({
                    form: this.new_team_form
                });
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
          '<div id=new-team-form-placeholder ',
              'class="yui3-overlay-indicator-content">',
              '<img src="/@@/spinner-big/">',
          '</div>',
          '<div class="extra-form-buttons hidden">',
              '<button class="yes_button" type="submit" ',
              'name="field.actions.create" value="Create Team">',
              'Create Team</button>',
              '<button class="no_button" type="button">Cancel</button>',
            '</div>',
          '</div>'].join('');
    },

    hide: function() {
        this.get('boundingBox').setStyle('display', 'none');
        // We want to cancel the new team form is there is one rendered.
        if (Y.Lang.isValue(this.new_team_form)
                && !this.new_team_form.hasClass('hidden')) {
            this.team_form_error_handler.clearFormErrors();
            this.hide_extra_content(this.new_team_form, false);
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

    /**
     * Show the submit spinner.
     *
     * @method _showSubmitSpinner
     */
    _showSubmitSpinner: function(submit_link) {
        var spinner_node = Y.Node.create(
        '<img class="spinner" src="/@@/spinner" alt="Creating..." />');
        submit_link.insert(spinner_node, 'after');
    },

    /**
     * Hide the submit spinner.
     *
     * @method _hideSubmitSpinner
     */
    _hideSubmitSpinner: function(submit_link) {
        var spinner = submit_link.get('parentNode').one('.spinner');
        if (spinner !== null) {
            spinner.remove(true);
        }
    },

    _cancel_new_team: function() {
        this.team_form_error_handler.clearFormErrors();
        this.hide_extra_content(this.new_team_form);
        this.set('centered', true);
    },

    _save_team_success: function(value) {
        this.hide_extra_content(this.new_team_form);
        this.fire('validate', value);
    },

    _save_new_team: function() {
        var submit_link = Y.one("[name='field.actions.create']");
        this.team_form_error_handler.showError =
            Y.bind(function (error_msg) {
                this._hideSubmitSpinner(submit_link);
                    this.team_form_error_handler.handleFormValidationError(
                        error_msg, [], []);
            }, this);

        var uri = Y.lp.client.get_absolute_uri('people/+simplenewteam');
        uri = uri.replace('api/devel', '');
        var form_data = {};
        this.new_team_form.all("[name^='field.']").each(function(field) {
            form_data[field.get('name')] = field.get('value');
        });
        form_data.id = this.new_team_form;
        var y_config = {
            method: "POST",
            headers: {'Accept': 'application/json;'},
            on: {
                start: Y.bind(function() {
                    this.team_form_error_handler.clearFormErrors();
                    this._showSubmitSpinner(submit_link);
                }, this),
                end:
                    Y.bind(this._hideSubmitSpinner, this, submit_link),
                failure: this.team_form_error_handler.getFailureHandler(),
                success:
                    Y.bind(
                        function(id, response, team_data) {
                            var value = {
                                "api_uri": "/~" + team_data['field.name'],
                                "title": team_data['field.dispayname'],
                                "value": team_data['field.name'],
                                "metadata": "team"};
                            this._save_team_success(value);
                        }, this)
            },
            'arguments': form_data
        };
        y_config.form = form_data;
        this.get("io_provider").io(uri, y_config);
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

        var on_success = function(id, response, picker) {
            Y.Array.each(picker.form_namespace.form_callbacks,
                function(callback_info) {
                Y.bind(
                    callback_info.callback, callback_info.picker,
                    response.responseText, true)();
            });
            picker.form_namespace.team_form = response.responseText;
        };
        var on_failure = function(id, response, picker) {
            Y.Array.each(picker.form_namespace.form_callbacks,
                function(callback_info) {
                Y.bind(
                    callback_info.callback, callback_info.picker,
                    'Sorry, an error occurred while loading the form.',
                    false)();
            });
        };
        var cfg = {
            on: {success: on_success, failure: on_failure},
            "arguments": this
            };
        var uri = Y.lp.client.get_absolute_uri(
            'people/+simplenewteam/++form++');
        uri = uri.replace('api/devel', '');
        this.get("io_provider").io(uri, cfg);
    },

    _render_new_team_form: function(form_html, show_submit) {
        // Poke the actual team form into the DOM and wire up the save and
        // cancel buttons.
        this.new_team_form.one('#new-team-form-placeholder')
            .replace(form_html);
        var form_callback = function(e, callback_fn) {
            e.halt();
            if (Y.Lang.isFunction(callback_fn) ) {
                Y.bind(callback_fn, this)();
            }
        };
        var submit_button = this.new_team_form.one(".yes_button");
        if (show_submit) {
            this.new_team_form.on('submit', function(e) {
                    e.halt();
                    this._save_new_team();
                }, this);
        } else {
            submit_button.addClass('hidden');
        }
        this.new_team_form.one(".no_button")
            .on('click', form_callback, this, this._cancel_new_team);
        this.new_team_form.one('.extra-form-buttons')
            .removeClass('hidden');
    },

    show_new_team_form: function() {
        this.show_extra_content(
            this.new_team_form, "Enter new team details");
        this.set('centered', true);
    },

    _assign_me_button_html: function() {
        return [
            '<a class="yui-picker-assign-me-button sprite person ',
            'js-action" href="javascript:void(0)" ',
            'style="padding-right: 1em">',
            this.get('assign_me_text'),
            '</a>'].join('');
    },

    _remove_button_html: function() {
        return [
            '<a class="yui-picker-remove-button sprite remove ',
            'js-action" href="javascript:void(0)" ',
            'style="padding-right: 1em">',
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
