YUI.add('lp.app.choice', function(Y) {

var namespace = Y.namespace('lp.app.choice');

function hook_up_spinner(widget) {
  // ChoiceSource makes assumptions about HTML in lazr-js
  // that don't hold true here, so we need to do our own
  // spinner icon and clear it when finished.
  Y.after(function() {
    var icon = this.get('editicon');
    icon.removeClass('edit');
    icon.addClass('update-in-progress-message');
    icon.setStyle('position', 'relative');
    icon.setStyle('bottom', '2px');
  }, widget, '_uiSetWaiting');
  Y.after(function() {
    var icon = this.get('editicon');
    icon.removeClass('update-in-progress-message');
    icon.addClass('edit');
    icon.setStyle('bottom', '0px');
  }, widget, '_uiClearWaiting');
}

namespace.addBinaryChoice = function(config, resource_uri, attribute) {
  var widget = new Y.ChoiceSource(config);
  widget.plug({
    fn: Y.lp.client.plugins.PATCHPlugin,
    cfg: {
      patch: attribute,
      resource: resource_uri}});
  hook_up_spinner(widget);
  widget.render();
};


namespace.addEnumChoice = function(config, resource_uri, attribute) {

  var widget = new Y.ChoiceSource(config);
  widget.plug({
    fn: Y.lp.client.plugins.PATCHPlugin,
    cfg: {
      patch: attribute,
      resource: resource_uri}});
  hook_up_spinner(widget);
  widget.on('save', function(e) {
      var cb = widget.get('contentBox');
      var value = widget.get('value');
      Y.Array.each(config.items, function(item) {
          if (item.value === value) {
            cb.one('span').addClass(item.css_class);
          } else {
            cb.one('span').removeClass(item.css_class);
          }
        });
    });
  widget.render();
};

namespace.addPopupChoice = function(field_name, choices) {
    var legacy_field_node = Y.one('[id=field.' + field_name + ']');
    var initial_field_value = legacy_field_node.get('value');

    var choice_node = Y.Node.create([
        '<span id="' + field_name + '-content"><span class="value"></span>',
        '<a class="sprite edit editicon" href="#"></a></span>'
        ].join(' '));

    legacy_field_node.insertBefore(choice_node, legacy_field_node);
    legacy_field_node.addClass('unseen');
    var field_content = Y.one('#' + field_name + '-content');

    var choice_edit = new Y.ChoiceSource({
        contentBox: field_content,
        value: initial_field_value,
        title: 'Set ' + field_name + " as",
        items: choices,
        elementToFlash: field_content
    });
    choice_edit.render();

    var update_selected_value_css = function(selected_value) {
        Y.Array.each(choices, function(item) {
            if (item.value === selected_value) {
                field_content.addClass(item.css_class);
            } else {
                field_content.removeClass(item.css_class);
            }
        });
    };
    update_selected_value_css(initial_field_value);
    choice_edit.on('save', function(e) {
        var selected_value = choice_edit.get('value');
        update_selected_value_css(selected_value);
        legacy_field_node.set('value', selected_value);
    });
};

}, "0.1", {"requires": ["lazr.choiceedit", "lp.client.plugins"]});
