// ProductFlow landing — "Greenfield" light deck. Vanilla JS, no framework, no build.
(function () {
  "use strict";

  document.documentElement.classList.remove("no-js");
  document.documentElement.classList.add("js");

  var prefersReduced = window.matchMedia
    ? window.matchMedia("(prefers-reduced-motion: reduce)")
    : { matches: false, addEventListener: function () {} };
  var reducedMotion = prefersReduced.matches;
  if (prefersReduced.addEventListener) {
    prefersReduced.addEventListener("change", function (e) { reducedMotion = e.matches; });
  }

  /* ============================================================
     STAGE DATA — verbatim names + per-stage mini-graphic that
     sells the FULL product (ER/DDL/API · 全栈+TDD · 部署上线).
     ============================================================ */
  var STAGES = [
    { n: "01", tag: "看板", title: "市场调研", desc: "竞品分析、核心矛盾梳理，产出产品 brief 与竞品矩阵。",
      art: '<div class="art-row"><span class="art-chip">brief.md</span><span class="art-chip">竞品矩阵</span></div>' },
    { n: "02", tag: "看板", title: "找参考", desc: "抓参考图、整页截图，登记成可点选的参考清单。",
      art: '<div class="art-canvas"><span></span><span></span><span></span><span></span></div>' },
    { n: "03", tag: "画布", title: "首图设计", desc: "批量出首图方案，铺到无限画布上缩放、点心、对比。",
      art: '<div class="art-canvas"><span></span><span class="lit"></span><span></span><span></span></div>' },
    { n: "04", tag: "画布", title: "页面设计", desc: "每个页面 × 每个平台的设计稿排到画布，页面地图盯版本。",
      art: '<div class="art-canvas"><span class="lit"></span><span></span><span class="lit"></span><span></span></div>' },
    { n: "05", tag: "看板", title: "功能与数据设计", desc: "模块清单、ER 图、表结构 DDL、API 契约，定清楚再动手。",
      art: '<div class="art-er"><span class="art-node">user</span><i class="art-link"></i><span class="art-node">project</span><i class="art-link"></i><span class="art-node">deploy</span></div><div class="art-row" style="margin-top:8px"><span class="art-chip">DDL</span><span class="art-chip">API 契约</span></div>' },
    { n: "06", tag: "看板", title: "开发实现", desc: "脚手架、前后端全栈、TDD 测试、接口文档，逐步登记。",
      art: '<div class="art-row"><span class="art-chip">前端</span><span class="art-chip">后端</span><span class="art-chip ok">TDD 通过 ✓</span></div>' },
    { n: "07", tag: "看板", title: "部署上线", desc: "本地 Docker、Cloudflare Pages/Workers 或单机，上线即出交付报告。",
      art: '<div class="art-deploy">▲ 已上线 · 127.0.0.1</div>' }
  ];

  var PRESETS = {
    saas: { label: "极简 SaaS", subject: "极简 SaaS" },
    portfolio: { label: "作品集", subject: "作品集" },
    waitlist: { label: "waitlist", subject: "waitlist" }
  };

  /* ============================================================
     STATE MACHINE
     ============================================================ */
  var rail = document.getElementById("stageRail");
  var nodes = rail ? Array.prototype.slice.call(rail.querySelectorAll(".rail-node")) : [];
  var termHost = document.getElementById("termHost");
  var railFill = document.getElementById("railFill");
  var prevTag = document.getElementById("prevTag");
  var prevStage = document.getElementById("prevStage");
  var prevTitle = document.getElementById("prevTitle");
  var prevDesc = document.getElementById("prevDesc");
  var prevArt = document.getElementById("prevArt");
  var status = document.getElementById("stageStatus");
  var runBtn = document.getElementById("runBtn");
  var presetSelect = document.getElementById("presetSelect");

  var currentStage = 4;     // default resting state: 04 页面设计 进行中
  var isAnimating = false;
  var runTimer = null;
  var introTimer = null;
  var preset = "saas";

  function statusWord(n) {
    if (n < currentStage) return "已完成";
    if (n === currentStage) return n === 7 ? "已上线" : "进行中";
    return "待办";
  }

  function renderRail() {
    nodes.forEach(function (node) {
      var n = parseInt(node.getAttribute("data-stage"), 10);
      node.classList.remove("done", "current");
      node.removeAttribute("aria-current");
      node.setAttribute("tabindex", n === currentStage ? "0" : "-1");
      if (n < currentStage) {
        node.classList.add("done");
      } else if (n === currentStage) {
        node.classList.add("current");
        node.setAttribute("aria-current", "step");
      }
    });
    // connector sweep: green fill grows left->right with progress
    if (railFill) {
      var pct = (currentStage - 1) / 6 * 100;
      railFill.style.width = pct + "%";
    }
  }

  function renderPreview() {
    var s = STAGES[currentStage - 1];
    if (prevTag) prevTag.textContent = s.tag;
    if (prevStage) prevStage.textContent = "阶段 " + s.n;
    if (prevTitle) prevTitle.textContent = s.title;
    if (prevDesc) prevDesc.textContent = s.desc;
    if (prevArt) prevArt.innerHTML = s.art;
    if (termHost) termHost.textContent = "127.0.0.1:7717 · stage " + s.n + "/07";
    if (status) {
      status.textContent = "阶段 " + s.n + " / " + s.title + " · " + statusWord(currentStage);
    }
  }

  // preview swap: 140ms cross-fade + 4px rise (transform/opacity only)
  var preview = document.getElementById("stagePreview");
  function setStage(n, opts) {
    opts = opts || {};
    n = Math.max(1, Math.min(7, n));
    currentStage = n;
    renderRail();
    if (preview && opts.animated && !reducedMotion) {
      preview.style.transition = "none";
      preview.style.opacity = "0";
      preview.style.transform = "translateY(4px)";
      renderPreview();
      // force reflow, then fade in
      void preview.offsetWidth;
      preview.style.transition = "opacity .14s var(--ease), transform .14s var(--ease)";
      preview.style.opacity = "1";
      preview.style.transform = "none";
    } else {
      if (preview) { preview.style.opacity = "1"; preview.style.transform = "none"; }
      renderPreview();
    }
  }

  /* ---------- drive path 1: rail node click + keyboard ---------- */
  function stopRun() {
    if (runTimer) { clearTimeout(runTimer); runTimer = null; }
    if (introTimer) { clearTimeout(introTimer); introTimer = null; }
    isAnimating = false;
    if (runBtn) runBtn.removeAttribute("disabled");
  }

  nodes.forEach(function (node) {
    node.addEventListener("click", function () {
      stopRun();                          // click always overrides autoplay
      var n = parseInt(node.getAttribute("data-stage"), 10);
      setStage(n, { animated: true });
      node.focus();
    });
  });

  if (rail) {
    rail.addEventListener("keydown", function (e) {
      var idx = nodes.indexOf(document.activeElement);
      if (idx === -1) return;
      var next = null;
      if (e.key === "ArrowRight" || e.key === "ArrowDown") next = idx + 1;
      else if (e.key === "ArrowLeft" || e.key === "ArrowUp") next = idx - 1;
      else if (e.key === "Home") next = 0;
      else if (e.key === "End") next = nodes.length - 1;
      else if (e.key === "Enter" || e.key === " ") {
        e.preventDefault();
        nodes[idx].click();
        return;
      } else return;
      e.preventDefault();
      next = Math.max(0, Math.min(nodes.length - 1, next));
      stopRun();
      setStage(next + 1, { animated: true });
      nodes[next].focus();
    });
  }

  /* ---------- drive path 2: ▶ 运行流水线 ---------- */
  function runPipeline() {
    stopRun();
    if (reducedMotion) {
      // jump straight to final state, no tween
      setStage(7, { animated: false });
      return;
    }
    isAnimating = true;
    if (runBtn) runBtn.setAttribute("disabled", "");
    setStage(1, { animated: true });
    var n = 1;
    function step() {
      n++;
      if (n > 7) { stopRun(); return; }
      setStage(n, { animated: true });
      runTimer = setTimeout(step, 260);
    }
    runTimer = setTimeout(step, 260);
  }
  if (runBtn) runBtn.addEventListener("click", runPipeline);

  /* ---------- drive path 3: prompt <select> re-themes ---------- */
  if (presetSelect) {
    presetSelect.addEventListener("change", function () {
      preset = presetSelect.value;
      void preset;            // subject re-theme is reflected in command line text already
      stopRun();
      renderPreview();
    });
  }

  // initial paint (resting state: 04 进行中)
  if (nodes.length) {
    setStage(4, { animated: false });
  }

  /* ---------- hero intro: ONE gentle cascade 01->04, rest on 04 ---------- */
  function heroIntro() {
    if (reducedMotion || !nodes.length) {
      setStage(4, { animated: false });   // render final resting state, no tween
      return;
    }
    setStage(1, { animated: true });
    var n = 1;
    function adv() {
      n++;
      if (n > 4) { return; }               // rest on 04 页面设计 · 进行中
      setStage(n, { animated: true });
      introTimer = setTimeout(adv, 340);
    }
    introTimer = setTimeout(adv, 600);
  }
  if (reducedMotion) {
    setStage(4, { animated: false });
  } else {
    setTimeout(heroIntro, 450);
  }

  /* ============================================================
     mobile nav (preserved contract)
     ============================================================ */
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
      if (menu.hidden) openMenu(); else closeMenu();
    });
    menu.addEventListener("click", function (e) {
      if (e.target.tagName === "A") closeMenu();
    });
    document.addEventListener("keydown", function (e) {
      if (e.key === "Escape" && !menu.hidden) { closeMenu(); toggle.focus(); }
    });
  }

  /* ============================================================
     copy install prompt (preserved contract + green check fade-in)
     ============================================================ */
  var copyBtn = document.getElementById("copyBtn");
  var promptEl = document.getElementById("installPrompt");

  function getPromptText() { return promptEl ? promptEl.textContent : ""; }

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
    try { ok = document.execCommand("copy"); } catch (err) { ok = false; }
    document.body.removeChild(ta);
    return ok;
  }

  var COPY_SVG = '<svg viewBox="0 0 24 24" width="15" height="15" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><rect x="9" y="9" width="11" height="11" rx="2"/><path d="M5 15V5a2 2 0 0 1 2-2h10"/></svg>';
  var CHECK_SVG = '<svg viewBox="0 0 24 24" width="15" height="15" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M20 6L9 17l-5-5"/></svg>';
  var BANG_SVG = '<svg viewBox="0 0 24 24" width="15" height="15" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M12 8v5M12 16.5v.5"/></svg>';

  var feedbackTimer = null;
  function showFeedback(success) {
    if (!copyBtn) return;
    var label = copyBtn.querySelector(".copy-label");
    var ico = copyBtn.querySelector(".copy-ico");
    if (feedbackTimer) clearTimeout(feedbackTimer);

    if (success) {
      copyBtn.classList.add("copied");
      if (label) label.textContent = "已复制";
      if (ico) ico.innerHTML = CHECK_SVG;
    } else {
      if (label) label.textContent = "复制失败，请手动选中";
      if (ico) ico.innerHTML = BANG_SVG;
    }
    feedbackTimer = setTimeout(function () {
      copyBtn.classList.remove("copied");
      if (label) label.textContent = "复制提示词";
      if (ico) ico.innerHTML = COPY_SVG;
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

  /* ============================================================
     scroll reveal (IntersectionObserver, one-shot, 40ms stagger)
     Under reduced motion: render final state, observers early-return.
     ============================================================ */
  var revealTargets = document.querySelectorAll(".reveal");
  function revealAll() {
    revealTargets.forEach(function (el) { el.classList.add("in"); });
  }
  if (reducedMotion || !("IntersectionObserver" in window)) {
    revealAll();
  } else {
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry, i) {
        if (entry.isIntersecting) {
          var el = entry.target;
          setTimeout(function () { el.classList.add("in"); }, (i % 6) * 40);
          io.unobserve(el);
        }
      });
    }, { threshold: 0, rootMargin: "0px 0px -8% 0px" });
    revealTargets.forEach(function (el) { io.observe(el); });
    setTimeout(revealAll, 2500);
    window.addEventListener("load", function () { setTimeout(revealAll, 400); });
  }
})();
