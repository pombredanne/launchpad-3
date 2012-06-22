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
        if (this.get('selected_value_metadata') === 'team') {
            var link_text = this.get('remove_team_text');
        } else {
            var link_text = this.get('remove_person_text');
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

    renderUI: function() {
        Y.lazr.picker.Picker.prototype.renderUI.apply(this, arguments);
        var extra_buttons = this.get('extra_buttons');
        var remove_button, assign_me_button;

        if (this.get('show_remove_button')) {
            remove_button = Y.Node.create(
                '<a class="yui-picker-remove-button bg-image" ' +
                'href="javascript:void(0)" ' +
                'style="background-image: url(/@@/remove); padding-right: ' +
                '1em">' + this.get('remove_person_text') + '</a>');
            remove_button.on('click', this.remove, this);
            extra_buttons.appendChild(remove_button);
            this.remove_button = remove_button;
        }

        if (this.get('show_assign_me_button')) {
            assign_me_button = Y.Node.create(
                '<a class="yui-picker-assign-me-button bg-image" ' +
                'href="javascript:void(0)" ' +
                'style="background-image: url(/@@/person)">' +
                this.get('assign_me_text') + '</a>');
            assign_me_button.on('click', this.assign_me, this);
            extra_buttons.appendChild(assign_me_button);
            this.assign_me_button = assign_me_button;
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
                return Y.Node.create('<div class="extra-form-buttons"/>')
            } 
        },
        show_assign_me_button: { value: true },
        show_remove_button: {value: true },
        assign_me_text: {value: 'Pick me'},
        remove_person_text: {value: 'Remove person'},
        remove_team_text: {value: 'Remove team'},
        min_search_chars: {value: 2}
    }
});
}, "0.1", {"requires": ["base", "node", "lazr.picker"]});
