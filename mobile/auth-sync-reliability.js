/* Web authentication and automatic sync reliability patch.
 * Keep the desktop-compatible password verifier as the authority; refresh the
 * shared account snapshot before attempting login so stale cached hashes do not
 * incorrectly reject valid credentials.
 */
(() => {
  const install = () => {
    const form = document.getElementById("appAuthForm");
    if (!form || form.dataset.cloudAuthRefreshInstalled === "1") return;
    form.dataset.cloudAuthRefreshInstalled = "1";
    document.addEventListener("submit", async (event) => {
      if (event.target !== form) return;
      event.preventDefault();
      event.stopImmediatePropagation();
      const username = document.getElementById("appAuthUsername")?.value || "";
      const password = document.getElementById("appAuthPassword")?.value || "";
      const submit = document.getElementById("btnAppSignIn");
      if (submit) submit.disabled = true;
      try {
        if (navigator.onLine && typeof pullFromCloud === "function") {
          await pullFromCloud(true);
        }
        if (typeof authenticateUser === "function") {
          await authenticateUser(username, password);
        }
      } finally {
        if (submit) submit.disabled = false;
      }
    }, true);

  };
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", install, { once: true });
  } else {
    install();
  }
})();
