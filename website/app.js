// Open-Trainer landing-page client.
// API base can be overridden with ?api=https://api.example.com for split deploys.
(function () {
  "use strict";
  const params = new URLSearchParams(window.location.search);
  const API = (params.get("api") || "").replace(/\/$/, "");
  const api = (path) => `${API}${path}`;

  // --- Landing: start checkout ---------------------------------------------
  function wireCheckoutButtons() {
    document.querySelectorAll("[data-checkout]").forEach((btn) => {
      btn.addEventListener("click", async () => {
        btn.disabled = true;
        const prev = btn.textContent;
        btn.textContent = "Redirecting…";
        try {
          const res = await fetch(api("/api/create-checkout-session"), { method: "POST" });
          if (!res.ok) throw new Error(await res.text());
          const data = await res.json();
          if (data.url) {
            window.location.href = data.url;
            return;
          }
          throw new Error("No checkout URL returned.");
        } catch (e) {
          const err = document.getElementById("checkout-error");
          if (err) {
            err.hidden = false;
            err.textContent = "Couldn't start checkout. Please try again.";
          }
          btn.disabled = false;
          btn.textContent = prev;
        }
      });
    });

    if (params.get("canceled")) {
      const banner = document.getElementById("canceled");
      if (banner) banner.hidden = false;
    }
  }

  // --- Success page: confirm payment, reveal the code ----------------------
  async function confirmCheckout() {
    const loading = document.getElementById("loading");
    const done = document.getElementById("done");
    const error = document.getElementById("error");
    const sessionId = params.get("session_id");
    if (!sessionId) {
      loading.hidden = true;
      error.hidden = false;
      return;
    }

    // Poll briefly in case the webhook is still settling.
    for (let attempt = 0; attempt < 6; attempt++) {
      try {
        const res = await fetch(api(`/api/checkout-status?session_id=${encodeURIComponent(sessionId)}`));
        if (res.ok) {
          const data = await res.json();
          if (data.paid && data.code) {
            document.getElementById("code").textContent = data.code;
            const link = document.getElementById("deep-link");
            if (data.deep_link) {
              link.href = data.deep_link;
              link.hidden = false;
            }
            loading.hidden = true;
            done.hidden = false;
            return;
          }
        }
      } catch (e) {
        /* retry */
      }
      await new Promise((r) => setTimeout(r, 1500));
    }
    loading.hidden = true;
    error.hidden = false;
  }

  if (document.getElementById("loading")) {
    confirmCheckout();
  } else {
    wireCheckoutButtons();
  }
})();
