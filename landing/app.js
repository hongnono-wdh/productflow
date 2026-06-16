// ProductFlow landing — vanilla JS. No framework, no build.
(function () {
  "use strict";

  /* ---------- mobile nav ---------- */
  var toggle = document.getElementById("navToggle");
  var menu = document.getElementById("mobileMenu");

  function closeMenu() {
    if (!menu || !toggle) return;
    menu.hidden = true;
    toggle.setAttribute("aria-expanded", "false");
    toggle.setAttribute("aria-label", "打开菜单");
  }
  function openMenu() {
    if (!menu || !toggle) return;
    menu.hidden = false;
    toggle.setAttribute("aria-expanded", "true");
    toggle.setAttribute("aria-label", "关闭菜单");
  }

  if (toggle && menu) {
    toggle.addEventListener("click", function () {
      if (menu.hidden) openMenu();
      else closeMenu();
    });
    // close after picking a destination
    menu.addEventListener("click", function (e) {
      if (e.target.tagName === "A") closeMenu();
    });
    document.addEventListener("keydown", function (e) {
      if (e.key === "Escape" && !menu.hidden) {
        closeMenu();
        toggle.focus();
      }
    });
  }

  /* ---------- copy install prompt ---------- */
  var copyBtn = document.getElementById("copyBtn");
  var promptEl = document.getElementById("installPrompt");

  function getPromptText() {
    // textContent decodes the HTML entities (&amp; -> &) to real shell text.
    return promptEl ? promptEl.textContent : "";
  }

  function legacyCopy(text) {
    var ta = document.createElement("textarea");
    ta.value = text;
    ta.setAttribute("readonly", "");
    ta.style.position = "fixed";
    ta.style.top = "-9999px";
    ta.style.opacity = "0";
    document.body.appendChild(ta);
    ta.select();
    ta.setSelectionRange(0, text.length);
    var ok = false;
    try {
      ok = document.execCommand("copy");
    } catch (err) {
      ok = false;
    }
    document.body.removeChild(ta);
    return ok;
  }

  var feedbackTimer = null;
  function showFeedback(success) {
    if (!copyBtn) return;
    var label = copyBtn.querySelector(".copy-label");
    var ico = copyBtn.querySelector(".copy-ico");
    if (feedbackTimer) clearTimeout(feedbackTimer);

    if (success) {
      copyBtn.classList.add("copied");
      if (label) label.textContent = "已复制";
      if (ico) ico.textContent = "✓";
    } else {
      if (label) label.textContent = "复制失败，请手动选中";
      if (ico) ico.textContent = "!";
    }

    feedbackTimer = setTimeout(function () {
      copyBtn.classList.remove("copied");
      if (label) label.textContent = "复制提示词";
      if (ico) ico.textContent = "⧉";
    }, 2200);
  }

  if (copyBtn && promptEl) {
    copyBtn.addEventListener("click", function () {
      var text = getPromptText();
      if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(text).then(
          function () { showFeedback(true); },
          function () { showFeedback(legacyCopy(text)); }
        );
      } else {
        showFeedback(legacyCopy(text));
      }
    });
  }

  /* ---------- scroll reveal (respects reduced motion) ---------- */
  var prefersReduced = window.matchMedia
    ? window.matchMedia("(prefers-reduced-motion: reduce)").matches
    : false;

  var revealTargets = document.querySelectorAll(
    ".sec-head, .stage, .cb, .feat, .strip-item, .hero-rail, .final-inner"
  );

  function revealAll() {
    revealTargets.forEach(function (el) { el.classList.add("in"); });
  }

  if (prefersReduced || !("IntersectionObserver" in window)) {
    revealAll();
  } else {
    revealTargets.forEach(function (el) { el.classList.add("reveal"); });
    var io = new IntersectionObserver(
      function (entries) {
        entries.forEach(function (entry) {
          if (entry.isIntersecting) {
            entry.target.classList.add("in");
            io.unobserve(entry.target);
          }
        });
      },
      { threshold: 0, rootMargin: "0px 0px -10% 0px" }
    );
    revealTargets.forEach(function (el) { io.observe(el); });

    // Safety net: nothing on this page should ever stay invisible. If the
    // observer somehow misses an element (tall section, odd layout, print),
    // force everything visible after a short grace period.
    setTimeout(revealAll, 2500);
    window.addEventListener("load", function () { setTimeout(revealAll, 400); });
  }
})();
