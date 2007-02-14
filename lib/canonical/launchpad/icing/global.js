function initHelpPanel() {
  /* 
    With CSS but no JavaScript, Launchpad is useful with the help always off,
    but not with the help always on, because it covers the page content.
    So the help panel is hidden by default. Then if JavaScript is available,
    this function hooks up the expand/collapse JavaScript to the panel, then
    reveals it in collapsed mode.
  */
  if (document.getElementById) {
    panel = document.getElementById('help_panel');
    panel.onclick = function() {
      if (panel.className == 'closed') {
        panel.className = 'open'
      } else {
        panel.className = 'closed'
      };
      return false;
    }
    panel.style.visibility = 'visible';
  }
}

function initPortlets() {
  if (document.getElementById) {
    portletContainer = document.getElementById('portlets');
    portlets = getElementsByTagAndClassName('div', 'portlet', portletContainer);
    actionsMenu = document.getElementById('actions');
    for (var i=0; i<portlets.length; ++i) {
      var portlet = portlets[i];
      if (portlet.getAttribute('id') != 'actions') {
        portlet.className = 'portlet collapsed';
        headings = getElementsByTagAndClassName('h2', null, portlet);
        if (headings.length > 0) {
          heading = headings[0];
          heading.onclick = function() {
            /* This assumes the portlet is the parent element of its heading: */
            portletToToggle = this.parentNode;
            if (portletToToggle.className == 'portlet collapsed') {
              portletToToggle.className = 'portlet expanded'
            } else {
              portletToToggle.className = 'portlet collapsed'
            };
          }
          heading.style.cursor = 'pointer';
          heading.style.cursor = 'hand';
        }
      }
    }
  }
}
