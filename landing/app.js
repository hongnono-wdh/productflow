// ProductFlow landing — "Glass Terminal" deck. Vanilla JS, no framework, no build.
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

  var isTouch = window.matchMedia
    ? window.matchMedia("(hover: none), (pointer: coarse)").matches
    : ("ontouchstart" in window);

  /* ============================================================
     STAGE DATA — verbatim source copy + view-tags per preset
     ============================================================ */
  var STAGES = [
    { n: "01", tag: "看板", title: "市场调研", desc: "竞品分析、核心矛盾梳理，产出产品 brief 与竞品矩阵。" },
    { n: "02", tag: "看板", title: "找参考", desc: "抓参考图、整页截图，登记成可点选的参考清单。" },
    { n: "03", tag: "画布", title: "首图设计", desc: "批量出首图方案，铺到无限画布上缩放、点心、对比。" },
    { n: "04", tag: "画布", title: "页面设计", desc: "每个页面 × 每个平台的设计稿排到画布，页面地图盯版本。" },
    { n: "05", tag: "看板", title: "功能与数据设计", desc: "模块清单、ER 图、表结构、API 约定，定清楚再动手。" },
    { n: "06", tag: "看板", title: "开发实现", desc: "脚手架、前后端、冒烟测试、接口文档，逐步登记。" },
    { n: "07", tag: "看板", title: "部署上线", desc: "本地 Docker、Cloudflare Pages/Workers 或单机，上线即出交付报告。" }
  ];

  var PRESETS = {
    saas: { label: "极简 SaaS", subject: "极简 SaaS" },
    portfolio: { label: "作品集", subject: "作品集" },
    waitlist: { label: "waitlist", subject: "waitlist 页" }
  };

  // log lines per stage; {subject} re-themed by the prompt <select>
  var LOG = {
    1: ["扫描 {subject} 同类竞品 …", "核心矛盾已梳理", "产出 brief + 竞品矩阵"],
    2: ["抓取参考图与整页截图 …", "登记 14 张可点选参考"],
    3: ["批量生成首图方案 …", "铺到无限画布，等你点心对比"],
    4: ["排布每页 × 每平台设计稿 …", "页面地图盯版本中"],
    5: ["生成模块清单 / ER 图 / 表结构 …", "API 约定已定"],
    6: ["脚手架 + 前后端落地 …", "冒烟测试通过"],
    7: ["构建 nginx:alpine 本地 Docker …", "E2E 8/8 ✓ · 本地 Docker 已上线"]
  };

  /* ============================================================
     STATE MACHINE
     ============================================================ */
  var rail = document.getElementById("stageRail");
  var nodes = rail ? Array.prototype.slice.call(rail.querySelectorAll(".rail-node")) : [];
  var termHost = document.getElementById("termHost");
  var termLog = document.getElementById("termLog");
  var prevTag = document.getElementById("prevTag");
  var prevStage = document.getElementById("prevStage");
  var prevTitle = document.getElementById("prevTitle");
  var prevDesc = document.getElementById("prevDesc");
  var status = document.getElementById("stageStatus");
  var runBtn = document.getElementById("runBtn");
  var presetSelect = document.getElementById("presetSelect");

  var currentStage = 4;     // default resting state mirrors the old hero
  var isAnimating = false;
  var runTimer = null;
  var typeTimer = null;
  var preset = "saas";

  function subject() { return PRESETS[preset].subject; }

  function statusWord(n) {
    if (n < currentStage) return "已完成";
    if (n === currentStage) return n === 7 ? "已完成" : "进行中";
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
  }

  function renderPreview() {
    var s = STAGES[currentStage - 1];
    if (prevTag) prevTag.textContent = s.tag;
    if (prevStage) prevStage.textContent = "阶段 " + s.n;
    if (prevTitle) prevTitle.textContent = s.title;
    if (prevDesc) prevDesc.textContent = s.desc;
    if (termHost) termHost.textContent = "127.0.0.1:7717 · stage " + s.n + "/07";
    if (status) {
      status.textContent = "阶段 " + s.n + " / " + s.title + " · " + statusWord(currentStage);
    }
  }

  // build the streaming log for stage n. animated = char-batch typing (appends only).
  function renderLog(n, animated) {
    if (!termLog) return;
    if (typeTimer) { clearTimeout(typeTimer); typeTimer = null; }
    termLog.innerHTML = "";

    var lines = (LOG[n] || []).map(function (l) {
      return l.replace("{subject}", subject());
    });
    // include a header line with the prompt
    var header = "$ pf run \"做一个 " + subject() + " 落地页\"";
    var allLines = [header].concat(lines.map(function (l) { return "› " + l; }));
    var finalLine = STAGES[n - 1].title;

    if (!animated) {
      // print fully, no tween
      allLines.forEach(function (text, i) {
        var div = document.createElement("span");
        div.className = "log-line " + (i === 0 ? "log-dim" : (i === allLines.length - 1 ? "log-ok" : ""));
        div.textContent = text;
        termLog.appendChild(div);
      });
      void finalLine;
      return;
    }

    // animated: append line by line, last line gets a caret
    var li = 0;
    function nextLine() {
      if (li >= allLines.length) return;
      var span = document.createElement("span");
      span.className = "log-line " + (li === 0 ? "log-dim" : (li === allLines.length - 1 ? "log-ok log-caret" : ""));
      // strip caret class from previous last line
      var prev = termLog.querySelector(".log-caret");
      if (prev) prev.classList.remove("log-caret");
      span.textContent = allLines[li];
      termLog.appendChild(span);
      li++;
      typeTimer = setTimeout(nextLine, 130);
    }
    nextLine();
  }

  // single source of truth
  function setStage(n, opts) {
    opts = opts || {};
    n = Math.max(1, Math.min(7, n));
    currentStage = n;
    renderRail();
    renderPreview();
    renderLog(n, opts.animated && !reducedMotion);
  }

  /* ---------- drive path 1: rail node click + keyboard ---------- */
  function stopRun() {
    if (runTimer) { clearTimeout(runTimer); runTimer = null; }
    isAnimating = false;
    if (runBtn) runBtn.removeAttribute("disabled");
  }

  nodes.forEach(function (node) {
    node.addEventListener("click", function () {
      stopRun();                          // click always overrides autoplay/scroll
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
      // jump straight to final state with full text, no tween
      setStage(7, { animated: false });
      return;
    }
    isAnimating = true;
    if (runBtn) runBtn.setAttribute("disabled", "");
    var n = 1;
    setStage(1, { animated: true });
    function step() {
      n++;
      if (n > 7) { stopRun(); return; }
      setStage(n, { animated: true });
      runTimer = setTimeout(step, 520);
    }
    runTimer = setTimeout(step, 520);
  }
  if (runBtn) runBtn.addEventListener("click", runPipeline);

  /* ---------- drive path 3: prompt <select> re-themes ---------- */
  if (presetSelect) {
    presetSelect.addEventListener("change", function () {
      preset = presetSelect.value;
      stopRun();
      // re-theme current stage log + preview labels (no stage change)
      renderLog(currentStage, false);
      renderPreview();
    });
  }

  // initial paint (resting state: 04 进行中)
  if (nodes.length) {
    setStage(4, { animated: false });
  }

  /* ---------- hero intro: type seed then ONE rail pass to 04 ---------- */
  function heroIntro() {
    if (reducedMotion || !nodes.length) {
      // reduced motion: render completed-ish resting state, log fully printed
      setStage(4, { animated: false });
      return;
    }
    var n = 1;
    setStage(1, { animated: true });
    function adv() {
      n++;
      if (n > 4) { return; }      // idle on 04 进行中 pulse
      setStage(n, { animated: n === 4 });
      typeTimer = setTimeout(adv, 360);
    }
    typeTimer = setTimeout(adv, 700);
  }
  // run intro shortly after load so the terminal "comes alive"
  setTimeout(heroIntro, 500);

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
     copy install prompt (preserved contract + SVG check-morph)
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
     scroll reveal (IntersectionObserver, one-shot)
     ============================================================ */
  var revealTargets = document.querySelectorAll(".reveal, .reveal-c");
  function revealAll() {
    revealTargets.forEach(function (el) { el.classList.add("in"); });
  }
  if (reducedMotion || !("IntersectionObserver" in window)) {
    revealAll();
  } else {
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (entry.isIntersecting) {
          entry.target.classList.add("in");
          io.unobserve(entry.target);
        }
      });
    }, { threshold: 0, rootMargin: "0px 0px -10% 0px" });
    revealTargets.forEach(function (el) { io.observe(el); });
    setTimeout(revealAll, 2500);
    window.addEventListener("load", function () { setTimeout(revealAll, 400); });
  }

  /* ============================================================
     scroll-morph graft (progressive enhancement, NOT load-bearing)
     #how cards crossing viewport midline advance the SAME terminal.
     Click always overrides (guarded by isAnimating + a user-click flag).
     ============================================================ */
  var userInterrupted = false;
  nodes.forEach(function (n) { n.addEventListener("click", function () { userInterrupted = true; }); });
  if (runBtn) runBtn.addEventListener("click", function () { userInterrupted = true; });

  if (!reducedMotion && !isTouch && "IntersectionObserver" in window) {
    var scrollCards = document.querySelectorAll("[data-scroll-stage]");
    var scrollIO = new IntersectionObserver(function (entries) {
      if (isAnimating || userInterrupted) return;     // never fight click/run
      entries.forEach(function (entry) {
        if (entry.isIntersecting && entry.intersectionRatio > 0.5) {
          var n = parseInt(entry.target.getAttribute("data-scroll-stage"), 10);
          if (n && n !== currentStage) setStage(n, { animated: false });
        }
      });
    }, { threshold: [0.5], rootMargin: "-30% 0px -30% 0px" });
    scrollCards.forEach(function (c) { scrollIO.observe(c); });
  }

  /* ============================================================
     EFFECT 1+2: parallax + cursor halo + terminal tilt
     ONE rAF loop, passive listeners, transform/opacity only.
     Early-returns under reduced motion.
     ============================================================ */
  if (!reducedMotion) {
    var halo = document.querySelector(".cursor-halo");
    var blobs = document.querySelector(".ambient");
    var mesh = document.querySelector(".mesh");
    var terminal = document.getElementById("terminal");

    var scrollY = window.pageYOffset || 0;
    var pointerX = window.innerWidth / 2;
    var pointerY = window.innerHeight / 2;
    var haloX = pointerX, haloY = pointerY;
    var tiltX = 0, tiltY = 0, targetTiltX = 0, targetTiltY = 0;
    var ticking = false;

    function onScroll() {
      scrollY = window.pageYOffset || document.documentElement.scrollTop || 0;
      requestTick();
    }
    function onMove(e) {
      pointerX = e.clientX;
      pointerY = e.clientY;
      if (halo) halo.style.opacity = "1";

      // terminal tilt from pointer position relative to its center
      if (terminal && !isTouch && window.innerWidth > 760) {
        var r = terminal.getBoundingClientRect();
        var cx = r.left + r.width / 2;
        var cy = r.top + r.height / 2;
        targetTiltY = Math.max(-5, Math.min(5, ((pointerX - cx) / r.width) * 10));
        targetTiltX = Math.max(-5, Math.min(5, -((pointerY - cy) / r.height) * 10));
      }
      requestTick();
    }
    function requestTick() {
      if (!ticking) { ticking = true; requestAnimationFrame(frame); }
    }
    function frame() {
      ticking = false;
      // parallax: blobs 0.15x, mesh 0.4x (written as CSS vars consumed by transforms)
      if (window.innerWidth > 768) {
        if (blobs) blobs.style.setProperty("--blob-y", (scrollY * -0.15) + "px");
        if (mesh) mesh.style.setProperty("--mesh-y", (scrollY * -0.4) + "px");
      }
      // halo lerp
      haloX += (pointerX - haloX) * 0.12;
      haloY += (pointerY - haloY) * 0.12;
      if (halo) halo.style.transform = "translate3d(" + haloX + "px," + haloY + "px,0)";
      // tilt lerp
      tiltX += (targetTiltX - tiltX) * 0.1;
      tiltY += (targetTiltY - tiltY) * 0.1;
      if (terminal && !isTouch && window.innerWidth > 760) {
        terminal.style.setProperty("--tilt-x", tiltX.toFixed(2) + "deg");
        terminal.style.setProperty("--tilt-y", tiltY.toFixed(2) + "deg");
      }
      // keep lerping until settled
      if (Math.abs(pointerX - haloX) > 0.5 || Math.abs(pointerY - haloY) > 0.5 ||
          Math.abs(targetTiltX - tiltX) > 0.05 || Math.abs(targetTiltY - tiltY) > 0.05) {
        requestTick();
      }
    }

    window.addEventListener("scroll", onScroll, { passive: true });
    window.addEventListener("pointermove", onMove, { passive: true });
    document.addEventListener("pointerleave", function () {
      targetTiltX = 0; targetTiltY = 0;
      if (halo) halo.style.opacity = "0";
      requestTick();
    });
    frame();

    /* magnetic CTAs */
    var magnets = document.querySelectorAll(".magnetic");
    magnets.forEach(function (el) {
      el.addEventListener("pointermove", function (e) {
        if (isTouch) return;
        var r = el.getBoundingClientRect();
        var mx = (e.clientX - (r.left + r.width / 2)) / (r.width / 2);
        var my = (e.clientY - (r.top + r.height / 2)) / (r.height / 2);
        var dx = Math.max(-1, Math.min(1, mx)) * 6;
        var dy = Math.max(-1, Math.min(1, my)) * 6;
        el.style.transform = "translate(" + dx + "px," + dy + "px) scale(1.03)";
      });
      el.addEventListener("pointerleave", function () {
        el.style.transform = "";
      });
    });
  }
})();
