YUI.add('lp.registry.personpicker', function(Y) {

var namespace = Y.namespace('lp.registry.personpicker');

var PersonPicker = function() {
    PersonPicker.superclass.constructor.apply(this, arguments);
};

Y.extend(PersonPicker, Y.lazr.Picker, {
    Y.after(this._renderUIPersonPicker, this, 'renderUI');

    _renderUIPersonPicker: function() {
        var extra_buttons = Y.Node.create('<div class="extra-form-buttons"/>');
        var remove_button, assign_me_button;
        //# TODO config should set extrabuttons
        var show_remove_button = true;
        var show_assign_me_button = true;
        if (show_remove_button) {
            remove_button = Y.Node.create(
                '<a class="yui-picker-remove-button bg-image" ' +
                'href="javascript:void(0)" ' +
                'style="background-image: url(/@@/remove); padding-right: 1em">' +
                remove_button_text + '</a>');
            remove_button.on('click', remove);
            extra_buttons.appendChild(remove_button);
        }
        if (show_assign_me_button) {
            assign_me_button = Y.Node.create(
                '<a class="yui-picker-assign-me-button bg-image" ' +
                'href="javascript:void(0)" ' +
                'style="background-image: url(/@@/person)">' +
                'Assign Me</a>');
            assign_me_button.on('click', assign_me);
            extra_buttons.appendChild(assign_me_button);
        }
        picker.set('footer_slot', extra_buttons);
    }
)};

}, "0.1", {"requires": []});
