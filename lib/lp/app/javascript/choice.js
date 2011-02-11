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
  widget.render();
};


}, "0.1", {"requires": ["lazr.choiceedit", "lp.client.plugins"]});
