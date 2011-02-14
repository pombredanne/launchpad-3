YUI.add('lp.app.choice', function(Y) {

var namespace = Y.namespace('lp.app.choice');

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
  widget.render();
};


}, "0.1", {"requires": ["lazr.choiceedit", "lp.client.plugins"]});
