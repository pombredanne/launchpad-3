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
    }
    panel.style.visibility = 'visible';
  }
}
