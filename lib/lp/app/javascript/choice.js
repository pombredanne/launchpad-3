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

  if (Y.UA.ie) {
    return;
  }

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

}, "0.1", {"requires": ["lazr.choiceedit", "lp.client.plugins"]});
