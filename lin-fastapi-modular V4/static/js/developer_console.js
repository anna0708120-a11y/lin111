(function () {
  const root = document.getElementById('console-sections');
  if (root && window.DeveloperConsole) {
    window.DeveloperConsole.mountFull(root);
    window.DeveloperConsole.refreshState();
  }
})();
