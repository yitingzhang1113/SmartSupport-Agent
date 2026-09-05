(function () {
  "use strict";

  var BASE = "http://localhost:8010";
  var API_PRODUCTS = BASE + "/api/products";
  var API_DETAIL = BASE + "/api/products/detail";
  var API_CHAT = BASE + "/api/langgraph/query";
  var PAGE = 12;

  // ---------- 信息架构：15 个类目归入 5 个一级场景 ----------
  var GROUPS = [
    { key: "security", label: "Security", title: "Security & Access", blurb: "Cameras, locks and sensors that keep an eye on the door.", cats: ["Smart Camera", "Smart Doorbell", "Smart Lock", "Security System", "Smart Sensor"] },
    { key: "entertainment", label: "Entertainment", title: "Entertainment", blurb: "Screens and speakers for every room.", cats: ["Smart TV", "Streaming Device", "Smart Speaker", "Smart Display"] },
    { key: "climate", label: "Climate", title: "Climate & Air", blurb: "Comfortable temperature, cleaner air.", cats: ["Smart Thermostat", "Air Purifier"] },
    { key: "lighting", label: "Lighting", title: "Lighting & Power", blurb: "Bulbs, strips and plugs you can schedule.", cats: ["Smart Lighting", "Smart Plug"] },
    { key: "cleaning", label: "Cleaning & Control", title: "Cleaning & Control", blurb: "Robot vacuums and the hubs that run the house.", cats: ["Robot Vacuum", "Home Hub"] }
  ];
  function groupByKey(k) { for (var i = 0; i < GROUPS.length; i++) if (GROUPS[i].key === k) return GROUPS[i]; return null; }
  function groupOfCat(c) { for (var i = 0; i < GROUPS.length; i++) if (GROUPS[i].cats.indexOf(c) >= 0) return GROUPS[i]; return null; }

  var SVG = {
    search: '<svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round"><circle cx="11" cy="11" r="7"/><path d="M20 20l-3.5-3.5"/></svg>',
    user: '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"><circle cx="12" cy="8" r="4"/><path d="M4 21c0-4 3.6-7 8-7s8 3 8 7"/></svg>',
    bag: '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linejoin="round"><path d="M6 8h12l1 13H5L6 8z"/><path d="M9 8V6a3 3 0 0 1 6 0v2"/></svg>',
    chat: '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linejoin="round"><path d="M4 5h16v11H9l-5 4V5z"/></svg>',
    close: '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round"><path d="M6 6l12 12M18 6L6 18"/></svg>',
    chev: '<svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round"><path d="M6 9l6 6 6-6"/></svg>',
    arrow: '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"><path d="M5 12h14M13 6l6 6-6 6"/></svg>'
  };

  // ---------- 工具 ----------
  function esc(s) {
    return String(s == null ? "" : s).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  }
  function money(n) { return "¥" + (Number(n) || 0).toLocaleString("zh-CN", { minimumFractionDigits: 2, maximumFractionDigits: 2 }); }
  function stockText(s) {
    if (s <= 0) return '<span class="hz-oos">Sold out</span>';
    if (s < 20) return '<span class="hz-low">Only ' + s + " left</span>";
    return '<span class="hz-ok">In stock</span>';
  }
  function thumb(p) {
    var ph = '<span class="hz-ico">' + esc(p.category) + "</span>";
    if (p.image) return ph + '<img class="hz-img" src="' + BASE + esc(p.image) + '" alt="" loading="lazy" onerror="this.remove()">';
    return ph;
  }
  function toast(msg) {
    var t = document.createElement("div"); t.className = "hz-toast"; t.textContent = msg;
    document.body.appendChild(t);
    setTimeout(function () { t.classList.add("show"); }, 10);
    setTimeout(function () { t.classList.remove("show"); setTimeout(function () { t.remove(); }, 300); }, 1700);
  }

  // ---------- 数据：一次拉全量，客户端筛选 ----------
  var ALL = null, allPromise = null;
  function loadAll() {
    if (allPromise) return allPromise;
    function attempt(n) {
      return fetch(API_PRODUCTS + "?limit=200", { cache: "no-store" })
        .then(function (r) { if (!r.ok) throw new Error("HTTP " + r.status); return r.json(); })
        .then(function (d) { ALL = (d && d.items) || []; return ALL; })
        .catch(function (e) {
          if (n > 0) return new Promise(function (res) { setTimeout(res, 800); }).then(function () { return attempt(n - 1); });
          allPromise = null;            // 允许后续再次尝试
          ALL = ALL || [];              // 失败也退化成空数组,避免 .slice() 崩溃
          return ALL;
        });
    }
    allPromise = attempt(5);
    return allPromise;
  }
  function findProduct(name) { if (!ALL) return null; for (var i = 0; i < ALL.length; i++) if (ALL[i].name === name) return ALL[i]; return null; }
  function brandList() {
    var m = {}; (ALL || []).forEach(function (p) { if (p.supplier) m[p.supplier] = (m[p.supplier] || 0) + 1; });
    return Object.keys(m).sort().map(function (k) { return { name: k, count: m[k] }; });
  }

  var CN2EN = { "智能音箱": "Smart Speaker", "音箱": "Smart Speaker", "智能显示器": "Smart Display", "智能屏": "Smart Display", "恒温器": "Smart Thermostat", "智能门铃": "Smart Doorbell", "门铃": "Smart Doorbell", "智能摄像头": "Smart Camera", "摄像头": "Smart Camera", "摄像机": "Smart Camera", "智能门锁": "Smart Lock", "门锁": "Smart Lock", "锁": "Smart Lock", "智能插座": "Smart Plug", "插座": "Smart Plug", "智能照明": "Smart Lighting", "智能灯": "Smart Lighting", "灯": "Smart Lighting", "扫地机器人": "Robot Vacuum", "扫地机": "Robot Vacuum", "吸尘器": "Robot Vacuum", "空气净化器": "Air Purifier", "净化器": "Air Purifier", "安防": "Security System", "流媒体": "Streaming Device", "智能电视": "Smart TV", "电视": "Smart TV", "家庭中枢": "Home Hub", "传感器": "Smart Sensor" };
  function toEn(q) { if (!q) return null; if (CN2EN[q]) return CN2EN[q]; var k = Object.keys(CN2EN).sort(function (a, b) { return b.length - a.length; }); for (var i = 0; i < k.length; i++) if (q.indexOf(k[i]) >= 0) return CN2EN[k[i]]; return null; }

  // ---------- 购物车 ----------
  function loadCart() { try { return JSON.parse(localStorage.getItem("biz_cart") || "[]"); } catch (e) { return []; } }
  function saveCart(c) { localStorage.setItem("biz_cart", JSON.stringify(c)); syncBadges(); }
  var cart = loadCart();
  function cartCount() { return cart.reduce(function (a, b) { return a + b.qty; }, 0); }
  function cartTotal() { return cart.reduce(function (a, b) { return a + b.qty * b.price; }, 0); }
  function addToCart(name, price, category, qty) {
    qty = qty || 1;
    var it = cart.find(function (x) { return x.name === name; });
    if (it) it.qty += qty; else cart.push({ name: name, price: Number(price) || 0, category: category || "", qty: qty });
    saveCart(cart); toast(qty > 1 ? "Added " + qty + " × " + name : "Added to cart · " + name);
  }
  function syncBadges() {
    var n = cartCount();
    document.querySelectorAll(".hz-cartcount").forEach(function (el) { el.textContent = n; el.style.display = n ? "flex" : "none"; });
  }

  // ================= 弹层（购物车 / 结算） =================
  var overlay, titleEl, bodyEl;
  function ensureModal() {
    if (overlay) return;
    overlay = document.createElement("div"); overlay.id = "hz-modal-ov";
    overlay.innerHTML =
      '<div class="hz-modal"><div class="hz-modal-head"><span class="hz-modal-title"></span><button class="hz-modal-close" aria-label="Close">' + SVG.close + "</button></div>" +
      '<div class="hz-modal-body"></div></div>';
    document.body.appendChild(overlay);
    titleEl = overlay.querySelector(".hz-modal-title"); bodyEl = overlay.querySelector(".hz-modal-body");
    overlay.querySelector(".hz-modal-close").addEventListener("click", hide);
    overlay.addEventListener("click", function (e) { if (e.target === overlay) hide(); });
  }
  function openModal(title) { ensureModal(); titleEl.textContent = title; overlay.style.display = "flex"; }
  function hide() { if (overlay) overlay.style.display = "none"; }

  function openCart() {
    openModal("Your cart");
    if (!cart.length) { bodyEl.innerHTML = '<div class="hz-loading">Your cart is empty.</div>'; return; }
    var h = '<div class="hz-cart">';
    cart.forEach(function (it, i) {
      var p = findProduct(it.name);
      var im = p && p.image ? '<img src="' + BASE + esc(p.image) + '" alt="" onerror="this.remove()">' : "";
      h += '<div class="hz-crow"><div class="hz-cico">' + im + "</div>" +
        '<div class="hz-cinfo"><div class="hz-cname">' + esc(it.name) + '</div><div class="hz-cprice">' + money(it.price) + "</div></div>" +
        '<div class="hz-cqty"><button class="hz-qbtn" data-cart="dec" data-i="' + i + '">−</button><span>' + it.qty + '</span><button class="hz-qbtn" data-cart="inc" data-i="' + i + '">+</button></div>' +
        '<button class="hz-cdel" data-cart="del" data-i="' + i + '">Remove</button></div>';
    });
    h += "</div><div class=\"hz-cfoot\"><div class=\"hz-ctotal\">Total <b>" + money(cartTotal()) + "</b></div>" +
      '<button class="hz-btn hz-btn-dark" data-cart="checkout">Checkout · ' + cartCount() + "</button></div>";
    bodyEl.innerHTML = h;
  }
  function checkout() {
    if (!cart.length) return;
    var n = cartCount(), amt = money(cartTotal()); cart = []; saveCart(cart);
    bodyEl.innerHTML = '<div class="hz-done"><div class="hz-done-ico">✓</div><h2>Order placed</h2>' +
      "<p>" + n + " item(s) · " + amt + "<br>Thank you for your purchase.</p>" +
      '<button class="hz-btn hz-btn-dark" data-cart="close">Continue shopping</button></div>';
  }

  // ================= AI 助手：右侧抽屉 =================
  var drawer, dBody, dInput, chatStarted = false;
  var SUGGEST = ["What is your return policy?", "Which smart locks work with Apple Home?", "How long does shipping take?"];
  function ensureDrawer() {
    if (drawer) return;
    drawer = document.createElement("div"); drawer.id = "hz-drawer";
    drawer.innerHTML =
      '<div class="hz-dr-scrim" data-dr="close"></div>' +
      '<aside class="hz-dr" role="dialog" aria-label="SmartSupport">' +
      '<div class="hz-dr-head"><div><div class="hz-dr-title">SmartSupport</div><div class="hz-dr-sub">Answers about products, orders and returns</div></div>' +
      '<button class="hz-dr-x" data-dr="close" aria-label="Close">' + SVG.close + "</button></div>" +
      '<div class="hz-dr-body" id="hz-dr-body"></div>' +
      '<div class="hz-dr-sugg" id="hz-dr-sugg">' + SUGGEST.map(function (s) { return '<button data-sugg="' + esc(s) + '">' + esc(s) + "</button>"; }).join("") + "</div>" +
      '<form class="hz-dr-foot" id="hz-dr-form"><input class="hz-dr-input" type="text" autocomplete="off" placeholder="Ask a question"/><button type="submit" class="hz-dr-send">Send</button></form></aside>';
    document.body.appendChild(drawer);
    dBody = drawer.querySelector("#hz-dr-body"); dInput = drawer.querySelector(".hz-dr-input");
    drawer.querySelector("#hz-dr-form").addEventListener("submit", function (e) { e.preventDefault(); sendChat(); });
    drawer.addEventListener("click", function (e) {
      var t = e.target.closest ? e.target.closest("[data-dr],[data-sugg]") : null; if (!t) return;
      if (t.hasAttribute("data-dr")) closeChat();
      else askAgent(t.getAttribute("data-sugg"));
    });
  }
  function openChat(prefill) {
    ensureDrawer();
    if (!chatStarted) { chatStarted = true; bubble("assistant", "Hi, I'm SmartSupport. Ask me about any product, your order, shipping or returns."); }
    drawer.classList.add("open"); document.documentElement.classList.add("hz-dr-open");
    if (prefill) dInput.value = prefill;
    setTimeout(function () { dInput.focus(); }, 60);
  }
  function closeChat() { if (drawer) { drawer.classList.remove("open"); document.documentElement.classList.remove("hz-dr-open"); } }
  function bubble(role, text) { var b = document.createElement("div"); b.className = "hz-bubble hz-" + role; b.textContent = text; dBody.appendChild(b); dBody.scrollTop = dBody.scrollHeight; return b; }
  function sendChat() { var q = (dInput.value || "").trim(); if (!q) return; dInput.value = ""; askAgent(q); }
  function askAgent(question) {
    var sg = drawer.querySelector("#hz-dr-sugg"); if (sg) sg.style.display = "none";
    bubble("user", question); var ans = bubble("assistant", "Thinking…"); ans.classList.add("hz-thinking"); var acc = "";
    var fd = new FormData(); fd.append("query", question); fd.append("user_id", localStorage.getItem("user_id") || "1");
    fetch(API_CHAT, { method: "POST", body: fd }).then(function (resp) {
      if (!resp.ok || !resp.body) throw new Error("HTTP " + resp.status);
      var reader = resp.body.getReader(), dec = new TextDecoder(), buf = "";
      function pump() {
        return reader.read().then(function (r) {
          if (r.done) return;
          buf += dec.decode(r.value, { stream: true }); var parts = buf.split("\n"); buf = parts.pop() || "";
          for (var i = 0; i < parts.length; i++) {
            var ln = parts[i]; if (ln.indexOf("data: ") !== 0) continue;
            var B = ln.slice(6); if (B === "[DONE]") continue;
            if (B.charAt(0) === '"' && B.charAt(B.length - 1) === '"' && B.length >= 2) B = B.slice(1, -1);
            B = B.replace(/\\n\\n/g, "\n\n").replace(/\\n/g, "\n").replace(/\\"/g, '"');
            acc += B; acc = acc.replace(/\{\s*["']\s*(done|interruption|error|decision)\s*["'][\s\S]*?\}/g, "");
            if (acc.trim()) { ans.textContent = acc; ans.classList.remove("hz-thinking"); } dBody.scrollTop = dBody.scrollHeight;
          }
          return pump();
        });
      }
      return pump();
    }).then(function () { ans.classList.remove("hz-thinking"); if (!acc.trim()) ans.textContent = "(no response)"; })
      .catch(function (err) { ans.classList.remove("hz-thinking"); ans.textContent = "Sorry, something went wrong: " + err.message; });
  }

  // ================= 商城页 =================
  var shop, gridEl, gridInfo, moreWrap, state = { items: [], shown: 0, title: "Featured", type: "featured", value: "", sort: "featured" };

  function megaHTML() {
    var cols = GROUPS.map(function (g) {
      return '<div class="hz-mega-col"><button class="hz-mega-h" data-group="' + g.key + '">' + esc(g.title) + "</button>" +
        g.cats.map(function (c) { return '<button class="hz-mega-l" data-cat="' + esc(c) + '">' + esc(c) + "</button>"; }).join("") + "</div>";
    }).join("");
    return '<div class="hz-menu hz-mega"><div class="hz-mega-in">' + cols +
      '<div class="hz-mega-col hz-mega-side"><button class="hz-mega-h" data-hz="shopall">All products ' + SVG.arrow + "</button><p>Every device in the store, from eight brands that already work together.</p>" +
      '<button class="hz-mega-l" data-hz="support">Not sure what fits? Ask SmartSupport</button></div></div></div>';
  }
  function headerHTML() {
    var nav = '<div class="hz-navitem hz-navitem-wide"><button class="hz-navlink" data-hz="shopall">Shop ' + SVG.chev + "</button>" + megaHTML() + "</div>";
    GROUPS.forEach(function (g) { nav += '<button class="hz-navlink" data-group="' + g.key + '">' + esc(g.label) + "</button>"; });
    nav += '<div class="hz-navitem"><button class="hz-navlink">Brands ' + SVG.chev + '</button><div class="hz-menu hz-menu-list" id="hz-brands"></div></div>';
    nav += '<button class="hz-navlink hz-navlink-mut" data-hz="support">Support</button>';
    return '<header class="hz-head"><div class="hz-head-in">' +
      '<a class="hz-brand" data-hz="home">SMARTSHOP</a>' +
      '<nav class="hz-nav">' + nav + "</nav>" +
      '<div class="hz-actions">' +
      '<label class="hz-searchwrap">' + SVG.search + '<input class="hz-search" type="search" placeholder="Search" aria-label="Search products"/></label>' +
      '<div class="hz-navitem hz-navitem-right"><button class="hz-iconbtn" aria-label="Account">' + SVG.user + "</button>" +
      '<div class="hz-menu hz-menu-list hz-menu-account"><button class="hz-mega-l" data-hz="cart">Cart</button><button class="hz-mega-l" data-hz="support">Help &amp; Support</button><a class="hz-mega-l hz-mega-mut" href="/">Agent console</a></div></div>' +
      '<button class="hz-iconbtn" data-hz="cart" aria-label="Cart">' + SVG.bag + '<span class="hz-cartcount">0</span></button>' +
      "</div></div></header>";
  }

  var HOME_HTML =
    '<section class="hz-hero"><div class="hz-hero-in"><div class="hz-eyebrow">Smart home</div>' +
    '<h1 class="hz-hero-h">Your home,<br>beautifully connected.</h1>' +
    '<p class="hz-hero-p">Locks, cameras, lighting and more. Devices from the brands you already trust, chosen to work together.</p>' +
    '<div class="hz-hero-cta"><button class="hz-btn hz-btn-dark" data-hz="shopall">Shop all products</button><button class="hz-btn hz-btn-line" data-group="security">Explore security</button></div></div></section>' +
    '<section class="hz-section"><div class="hz-section-head"><h2>Shop by category</h2></div><div class="hz-tiles" id="hz-tiles"></div></section>' +
    '<section class="hz-section" id="hz-listing"><div class="hz-section-head"><div><div class="hz-crumb" id="hz-crumb"></div><h2 id="hz-grid-title">Featured</h2></div><span class="hz-section-sub" id="hz-grid-info"></span></div>' +
    '<div class="hz-filters"><div class="hz-chips" id="hz-chips"></div><select class="hz-sort" id="hz-sort" aria-label="Sort"><option value="featured">Sort: Featured</option><option value="asc">Price: low to high</option><option value="desc">Price: high to low</option></select></div>' +
    '<div class="hz-grid" id="hz-grid"></div><div class="hz-more" id="hz-more"></div></section>' +
    '<footer class="hz-foot"><div class="hz-foot-in">' +
    '<div class="hz-foot-col hz-foot-brandcol"><div class="hz-foot-brand">SMARTSHOP</div><p>Curated smart-home devices. Demo storefront over Business_data.</p></div>' +
    '<div class="hz-foot-col"><h4>Shop</h4>' + GROUPS.map(function (g) { return '<button data-group="' + g.key + '">' + esc(g.title) + "</button>"; }).join("") + "</div>" +
    '<div class="hz-foot-col"><h4>Help</h4><button data-hz="support">Chat with SmartSupport</button><button data-ask="What is your return and refund policy?">Returns &amp; refunds</button><button data-ask="What are the shipping options and delivery times?">Shipping</button><button data-ask="How does the warranty work?">Warranty</button></div>' +
    '<div class="hz-foot-col"><h4>Company</h4><button data-hz="home">Home</button><a href="/">Agent console</a></div>' +
    '</div><div class="hz-foot-bottom">© SmartShop · Powered by SmartSupport</div></footer>';

  function buildShop() {
    if (shop) return;
    shop = document.createElement("div"); shop.id = "hz-shop";
    shop.innerHTML = '<div class="hz-announce"><span class="hz-announce-mid">Free shipping on orders over ¥999</span><a class="hz-announce-back" href="/">← Back to SmartSupport Assistant</a></div>' + headerHTML() + '<main id="hz-main"></main>';
    var fab = document.createElement("button"); fab.className = "hz-cs-fab"; fab.setAttribute("data-hz", "support");
    fab.innerHTML = SVG.chat + "<span>Need help?</span>";
    shop.appendChild(fab);
    document.body.appendChild(shop);
    renderHome();
    syncBadges();
    loadAll().then(function () {
      var b = shop.querySelector("#hz-brands");
      if (b) b.innerHTML = brandList().map(function (x) { return '<button class="hz-mega-l" data-brand="' + esc(x.name) + '">' + esc(x.name) + "<span>" + x.count + "</span></button>"; }).join("");
      fillTiles(); applyListing();
    });
  }

  function renderHome() {
    var main = shop.querySelector("#hz-main"); main.innerHTML = HOME_HTML;
    gridEl = main.querySelector("#hz-grid"); gridInfo = main.querySelector("#hz-grid-info"); moreWrap = main.querySelector("#hz-more");
    main.querySelector("#hz-sort").value = state.sort;
    if (ALL) { fillTiles(); applyListing(); } else gridEl.innerHTML = '<div class="hz-loading">Loading…</div>';
  }
  function onHome() { return shop && shop.querySelector("#hz-grid"); }
  function goHome() { if (shop && !onHome()) renderHome(); }

  function fillTiles() {
    var el = shop.querySelector("#hz-tiles"); if (!el || !ALL) return;
    el.innerHTML = GROUPS.map(function (g) {
      var items = ALL.filter(function (p) { return g.cats.indexOf(p.category) >= 0; });
      var pic = items.filter(function (p) { return p.image; })[0];
      return '<button class="hz-tile" data-group="' + g.key + '"><div class="hz-tile-img">' + (pic ? '<img src="' + BASE + esc(pic.image) + '" alt="" loading="lazy" onerror="this.remove()">' : '<span class="hz-ico">' + esc(g.label) + "</span>") + "</div>" +
        '<div class="hz-tile-t">' + esc(g.title) + '</div><div class="hz-tile-s">' + items.length + " products</div></button>";
    }).join("");
  }

  // 列表：type = featured | all | group | cat | brand | search
  function showListing(type, value) {
    state.type = type; state.value = value || ""; state.shown = PAGE;
    goHome();
    applyListing();
    var sec = shop.querySelector("#hz-listing");
    if (sec && type !== "featured") shop.scrollTop = Math.max(0, sec.offsetTop - 72);
  }
  function applyListing() {
    if (!ALL || !onHome()) return;
    var items = ALL.slice(), title = "Featured", crumb = "", chips = "";
    var t = state.type, v = state.value, g;
    if (t === "all") { title = "All products"; crumb = "Home / All products"; chips = chipRow(GROUPS.map(function (x) { return { k: "group", v: x.key, l: x.label }; }), null); }
    else if (t === "group" && (g = groupByKey(v))) {
      items = items.filter(function (p) { return g.cats.indexOf(p.category) >= 0; }); title = g.title; crumb = "Home / " + g.title;
      chips = chipRow([{ k: "group", v: g.key, l: "All " + g.label.toLowerCase() }].concat(g.cats.map(function (c) { return { k: "cat", v: c, l: c }; })), "group:" + g.key);
    } else if (t === "cat") {
      items = items.filter(function (p) { return p.category === v; }); title = v; g = groupOfCat(v); crumb = "Home / " + (g ? g.title : "Categories");
      if (g) chips = chipRow([{ k: "group", v: g.key, l: "All " + g.label.toLowerCase() }].concat(g.cats.map(function (c) { return { k: "cat", v: c, l: c }; })), "cat:" + v);
    } else if (t === "brand") { items = items.filter(function (p) { return p.supplier === v; }); title = v; crumb = "Home / Brands"; }
    else if (t === "search") {
      var q = v.toLowerCase(), en = (toEn(v) || "").toLowerCase();
      items = items.filter(function (p) { var s = (p.name + " " + p.category + " " + p.supplier).toLowerCase(); return s.indexOf(q) >= 0 || (en && s.indexOf(en) >= 0); });
      title = 'Results for "' + v + '"'; crumb = "Home / Search";
    }
    if (state.sort === "asc") items.sort(function (a, b) { return a.price - b.price; });
    else if (state.sort === "desc") items.sort(function (a, b) { return b.price - a.price; });
    state.items = items; state.title = title; if (!state.shown) state.shown = PAGE;
    shop.querySelector("#hz-grid-title").textContent = title;
    shop.querySelector("#hz-crumb").innerHTML = crumb ? esc(crumb) : "";
    shop.querySelector("#hz-chips").innerHTML = chips;
    gridInfo.textContent = items.length + (items.length === 1 ? " product" : " products");
    renderGrid();
  }
  function chipRow(list, active) {
    return list.map(function (c) {
      var on = active === (c.k + ":" + c.v) ? " hz-chip-on" : "";
      return '<button class="hz-chip' + on + '" data-' + (c.k === "group" ? "group" : "cat") + '="' + esc(c.v) + '">' + esc(c.l) + "</button>";
    }).join("");
  }
  function renderGrid() {
    if (!state.items.length) { gridEl.innerHTML = '<div class="hz-loading">No products match. Try another category or ask SmartSupport.</div>'; moreWrap.innerHTML = ""; return; }
    var html = "";
    state.items.slice(0, state.shown).forEach(function (p) {
      html += '<article class="hz-card" data-name="' + esc(p.name) + '">' +
        '<div class="hz-thumb">' + thumb(p) + "</div>" +
        '<div class="hz-cat">' + esc(p.supplier || p.category) + "</div>" +
        '<h3 class="hz-name">' + esc(p.name) + "</h3>" +
        '<div class="hz-cardbot"><span class="hz-price">' + money(p.price) + "</span>" + stockText(p.stock) + "</div>" +
        '<button class="hz-btn hz-btn-line hz-add" data-act="cart" data-name="' + esc(p.name) + '" data-price="' + p.price + '" data-cat="' + esc(p.category) + '">Add to cart</button></article>';
    });
    gridEl.innerHTML = html;
    moreWrap.innerHTML = state.shown < state.items.length ? '<button class="hz-btn hz-btn-line" data-hz="more">Show more (' + (state.items.length - state.shown) + ")</button>" : "";
  }

  // ---------- 商品详情页 ----------
  function renderPDP(name) {
    if (!shop) buildShop();
    var main = shop.querySelector("#hz-main");
    shop.scrollTop = 0; main.innerHTML = '<div class="hz-pdp-load">Loading…</div>';
    fetch(API_DETAIL + "?name=" + encodeURIComponent(name)).then(function (r) { if (!r.ok) throw 0; return r.json(); })
      .then(function (p) {
        loadAll().then(function () {
          var related = ALL.filter(function (x) { return x.category === p.category && x.name !== p.name; }).slice(0, 4);
          main.innerHTML = pdpHTML(p, related); shop.scrollTop = 0;
        });
      }).catch(function () { main.innerHTML = '<div class="hz-pdp-load">Product not found</div>'; });
  }
  function pdpHTML(p, related) {
    var g = groupOfCat(p.category);
    var img = p.image ? '<img class="hz-pdp-img" src="' + BASE + esc(p.image) + '" alt="" onerror="this.style.display=\'none\'">' : "";
    var stockLine = p.stock > 0 ? '<span class="hz-ok">In stock · ' + p.stock + " available</span>" : '<span class="hz-oos">Sold out</span>';
    var rel = "";
    if (related.length) {
      rel = '<div class="hz-pdp-rel"><h2>More in ' + esc(p.category) + '</h2><div class="hz-grid">';
      related.forEach(function (r) {
        rel += '<article class="hz-card" data-name="' + esc(r.name) + '"><div class="hz-thumb">' + thumb(r) + '</div><div class="hz-cat">' + esc(r.supplier || r.category) + '</div><h3 class="hz-name">' + esc(r.name) + '</h3><div class="hz-cardbot"><span class="hz-price">' + money(r.price) + "</span>" + stockText(r.stock) + "</div></article>";
      });
      rel += "</div></div>";
    }
    return '<div class="hz-pdp">' +
      '<div class="hz-crumb"><a data-hz="home">Home</a> / ' + (g ? '<a data-group="' + g.key + '">' + esc(g.title) + "</a> / " : "") + '<a data-cat="' + esc(p.category) + '">' + esc(p.category) + "</a> / <span>" + esc(p.name) + "</span></div>" +
      '<div class="hz-pdp-grid">' +
      '<div class="hz-pdp-frame"><span class="hz-ico">' + esc(p.category) + "</span>" + img + "</div>" +
      '<div class="hz-pdp-info">' +
      '<div class="hz-pdp-brand">' + esc(p.supplier) + "</div>" +
      '<h1 class="hz-pdp-name">' + esc(p.name) + "</h1>" +
      '<div class="hz-pdp-price">' + money(p.price) + "</div>" +
      '<div class="hz-pdp-stock">' + stockLine + "</div>" +
      '<div class="hz-pdp-qtyrow"><span>Quantity</span><div class="hz-qsel"><button data-pdp="qminus">−</button><span id="hz-qty">1</span><button data-pdp="qplus">+</button></div></div>' +
      '<div class="hz-pdp-actions">' +
      '<button class="hz-btn hz-btn-dark" data-pdp="addcart" data-name="' + esc(p.name) + '" data-price="' + p.price + '" data-cat="' + esc(p.category) + '">Add to cart</button>' +
      '<button class="hz-btn hz-btn-line" data-pdp="buynow" data-name="' + esc(p.name) + '" data-price="' + p.price + '" data-cat="' + esc(p.category) + '">Buy it now</button></div>' +
      '<div class="hz-pdp-ask"><button data-act="ask" data-name="' + esc(p.name) + '">' + SVG.chat + " Ask SmartSupport about this product</button></div>" +
      '<div class="hz-pdp-desc"><h3>Details</h3><p>' + esc(p.name) + " by " + esc(p.supplier) + ", from our " + esc(p.category) + " range. Sold as " + esc(p.quantityPerUnit || "a standard unit") + ".</p>" +
      '<table class="hz-spec"><tr><td>Category</td><td>' + esc(p.category) + "</td></tr><tr><td>Brand</td><td>" + esc(p.supplier) + "</td></tr><tr><td>Packaging</td><td>" + esc(p.quantityPerUnit || "Standard unit") + "</td></tr><tr><td>Availability</td><td>" + (p.stock > 0 ? p.stock + " in stock" : "Sold out") + "</td></tr><tr><td>SKU</td><td>#" + esc(p.id) + "</td></tr></table></div>" +
      "</div></div>" + rel + "</div>";
  }

  // ---------- 路由 ----------
  function onShop() { return location.pathname.indexOf("/ecommerce") === 0; }
  function toggleShop() {
    if (onShop()) { buildShop(); shop.style.display = "block"; document.documentElement.classList.add("hz-lock"); }
    else if (shop) { shop.style.display = "none"; document.documentElement.classList.remove("hz-lock"); closeChat(); }
  }

  // ================= 事件 =================
  function closeMenus(from) { var ni = from && from.closest ? from.closest(".hz-navitem") : null; if (ni) ni.querySelectorAll(".hz-menu").forEach(function (m) { m.classList.add("hz-closed"); }); }
  document.addEventListener("mouseover", function (e) {
    var t = e.target; if (!t || !t.closest) return;
    var ni = t.closest(".hz-navitem"); if (!ni) return;
    if (!ni.dataset.armed) { ni.dataset.armed = "1"; ni.addEventListener("mouseleave", function () { ni.querySelectorAll(".hz-closed").forEach(function (m) { m.classList.remove("hz-closed"); }); }); }
  });

  document.addEventListener("click", function (e) {
    var t = e.target; if (!t || !t.closest || !shop || !shop.contains(t)) return;

    var cc = t.closest("[data-cart]");
    if (cc) { return; }

    var act = t.closest("[data-act]");
    if (act) {
      e.preventDefault(); e.stopPropagation(); var an = act.getAttribute("data-name");
      if (act.getAttribute("data-act") === "cart") addToCart(an, act.getAttribute("data-price"), act.getAttribute("data-cat"));
      else if (act.getAttribute("data-act") === "ask") openChat("Tell me about " + an + ": price, stock and what it works with.");
      return;
    }
    var ask = t.closest("[data-ask]");
    if (ask) { e.preventDefault(); openChat(); askAgent(ask.getAttribute("data-ask")); return; }

    var pdp = t.closest("[data-pdp]");
    if (pdp) {
      e.preventDefault(); var pk = pdp.getAttribute("data-pdp");
      if (pk === "qminus" || pk === "qplus") {
        var qel = document.getElementById("hz-qty"); var v = parseInt(qel.textContent, 10) || 1;
        v += pk === "qplus" ? 1 : -1; if (v < 1) v = 1; qel.textContent = v;
      } else if (pk === "addcart" || pk === "buynow") {
        var qe = document.getElementById("hz-qty"); var n = parseInt(qe ? qe.textContent : "1", 10) || 1;
        addToCart(pdp.getAttribute("data-name"), pdp.getAttribute("data-price"), pdp.getAttribute("data-cat"), n);
        if (pk === "buynow") openCart();
      }
      return;
    }
    var grp = t.closest("[data-group]");
    if (grp) { e.preventDefault(); closeMenus(grp); showListing("group", grp.getAttribute("data-group")); return; }
    var cat = t.closest("[data-cat]");
    if (cat) { e.preventDefault(); closeMenus(cat); showListing("cat", cat.getAttribute("data-cat")); return; }
    var br = t.closest("[data-brand]");
    if (br) { e.preventDefault(); closeMenus(br); showListing("brand", br.getAttribute("data-brand")); return; }

    var hz = t.closest("[data-hz]");
    if (hz) {
      e.preventDefault(); var k = hz.getAttribute("data-hz"); closeMenus(hz);
      if (k === "cart") openCart();
      else if (k === "support") openChat();
      else if (k === "shopall") showListing("all", "");
      else if (k === "home") { state.type = "featured"; state.value = ""; state.shown = PAGE; goHome(); applyListing(); shop.scrollTop = 0; }
      else if (k === "more") { state.shown += PAGE; renderGrid(); }
      return;
    }
    var card = t.closest(".hz-card");
    if (card) { e.preventDefault(); renderPDP(card.getAttribute("data-name")); return; }
  }, true);

  // 购物车弹层内的操作（弹层挂在 body 上）
  document.addEventListener("click", function (e) {
    var t = e.target; if (!t || !t.closest || !overlay || !overlay.contains(t)) return;
    var cc = t.closest("[data-cart]"); if (!cc) return;
    e.preventDefault(); var a = cc.getAttribute("data-cart"), i = parseInt(cc.getAttribute("data-i"), 10);
    if (a === "inc") { cart[i].qty++; saveCart(cart); openCart(); }
    else if (a === "dec") { cart[i].qty--; if (cart[i].qty <= 0) cart.splice(i, 1); saveCart(cart); openCart(); }
    else if (a === "del") { cart.splice(i, 1); saveCart(cart); openCart(); }
    else if (a === "checkout") checkout(); else if (a === "close") hide();
  });

  document.addEventListener("keydown", function (e) {
    if (e.key === "Escape") { closeChat(); hide(); return; }
    if (e.key !== "Enter" || !e.target || !e.target.classList || !e.target.classList.contains("hz-search")) return;
    var q = e.target.value.trim(); if (!q) return; e.preventDefault(); showListing("search", q);
  });
  document.addEventListener("change", function (e) {
    if (e.target && e.target.id === "hz-sort") { state.sort = e.target.value; applyListing(); }
  });

  // ---------- 样式 ----------
  var css = document.createElement("style");
  css.textContent =
    ":root{--hz-ink:#171717;--hz-mut:#737373;--hz-line:#e7e5e4;--hz-bg:#ffffff;--hz-soft:#f5f4f2}" +
    "html.hz-lock,html.hz-lock body{overflow:auto}" +
    "#hz-shop{display:none;position:fixed;inset:0;overflow-y:auto;z-index:9000;background:var(--hz-bg);color:var(--hz-ink);font-family:'Helvetica Neue',Helvetica,system-ui,-apple-system,'Segoe UI',Arial,sans-serif;-webkit-font-smoothing:antialiased}" +
    "#hz-shop button{font-family:inherit}" +
    ".hz-announce{position:relative;background:var(--hz-ink);color:#fff;text-align:center;font-size:11px;letter-spacing:.1em;padding:8px 12px;text-transform:uppercase}.hz-announce-back{position:absolute;right:16px;top:50%;transform:translateY(-50%);color:#fff;text-decoration:none;opacity:.85;font-weight:600}.hz-announce-back:hover{opacity:1;text-decoration:underline}@media(max-width:700px){.hz-announce-mid{display:none}.hz-announce-back{position:static;transform:none}}" +
    // 顶栏
    ".hz-head{position:sticky;top:0;z-index:20;background:rgba(255,255,255,.94);backdrop-filter:saturate(1.2) blur(10px);border-bottom:1px solid var(--hz-line)}" +
    ".hz-head-in{max-width:1280px;margin:0 auto;padding:0 32px;height:64px;display:flex;align-items:center;gap:32px}" +
    ".hz-brand{font-weight:800;font-size:18px;letter-spacing:.18em;cursor:pointer;text-decoration:none;color:var(--hz-ink);white-space:nowrap}" +
    ".hz-nav{display:flex;align-items:center;gap:4px;height:100%}" +
    ".hz-navitem{height:100%;display:flex;align-items:center;position:relative}.hz-navitem-wide{position:static}" +
    ".hz-navlink{display:inline-flex;align-items:center;gap:5px;height:100%;padding:0 12px;border:none;background:none;font-size:14px;color:var(--hz-ink);cursor:pointer;white-space:nowrap;border-bottom:2px solid transparent}" +
    ".hz-navlink:hover,.hz-navitem:hover>.hz-navlink{border-bottom-color:var(--hz-ink)}.hz-navlink-mut{color:var(--hz-mut)}.hz-navlink-mut:hover{color:var(--hz-ink)}" +
    ".hz-menu{display:none;position:absolute;top:100%;background:#fff;border:1px solid var(--hz-line);border-top:none;box-shadow:0 24px 48px -24px rgba(0,0,0,.25);z-index:30}" +
    ".hz-navitem:hover>.hz-menu:not(.hz-closed),.hz-navitem:focus-within>.hz-menu:not(.hz-closed){display:block}" +
    ".hz-mega{left:0;right:0}.hz-mega-in{max-width:1280px;margin:0 auto;padding:32px 32px 36px;display:grid;grid-template-columns:repeat(5,1fr) 1.2fr;gap:24px}" +
    ".hz-mega-col{display:flex;flex-direction:column;align-items:flex-start;gap:2px}" +
    ".hz-mega-h{border:none;background:none;padding:0 0 10px;font-size:13px;font-weight:700;letter-spacing:.06em;text-transform:uppercase;color:var(--hz-ink);cursor:pointer;text-align:left;display:inline-flex;align-items:center;gap:6px}.hz-mega-h:hover{text-decoration:underline}" +
    ".hz-mega-l{border:none;background:none;padding:6px 0;font-size:14px;color:var(--hz-mut);cursor:pointer;text-align:left;text-decoration:none;display:flex;justify-content:space-between;gap:16px;width:100%}.hz-mega-l:hover{color:var(--hz-ink)}.hz-mega-l span{color:#b5b5b5;font-size:12px}.hz-mega-mut{color:#a3a3a3;font-size:13px}" +
    ".hz-mega-side{border-left:1px solid var(--hz-line);padding-left:24px}.hz-mega-side p{margin:0 0 14px;font-size:13px;line-height:1.6;color:var(--hz-mut)}" +
    ".hz-menu-list{min-width:220px;padding:10px 18px}.hz-menu-list .hz-mega-l{padding:8px 0}" +
    ".hz-navitem-right{position:relative}.hz-menu-account{left:auto;right:0;top:calc(100% - 8px)}" +
    ".hz-actions{margin-left:auto;display:flex;align-items:center;gap:6px}" +
    ".hz-searchwrap{display:flex;align-items:center;gap:8px;border:1px solid var(--hz-line);padding:0 12px;height:38px;width:200px;color:var(--hz-mut);transition:.15s}.hz-searchwrap:focus-within{border-color:var(--hz-ink);width:260px;color:var(--hz-ink)}" +
    ".hz-search{border:none;outline:none;background:none;font-size:14px;flex:1;min-width:0;color:var(--hz-ink);font-family:inherit}.hz-search::-webkit-search-cancel-button{display:none}" +
    ".hz-iconbtn{position:relative;width:38px;height:38px;border:none;background:none;color:var(--hz-ink);cursor:pointer;display:inline-flex;align-items:center;justify-content:center;border-radius:50%}.hz-iconbtn:hover{background:var(--hz-soft)}" +
    ".hz-cartcount{position:absolute;top:2px;right:0;background:var(--hz-ink);color:#fff;font-size:10px;min-width:16px;height:16px;border-radius:8px;display:none;align-items:center;justify-content:center;padding:0 4px}" +
    "@media(max-width:1180px){.hz-nav>.hz-navlink[data-group]{display:none}}@media(max-width:860px){.hz-head-in{gap:16px;padding:0 20px}.hz-searchwrap{width:44px;padding:0 12px}.hz-searchwrap:focus-within{width:180px}.hz-search{display:none}.hz-searchwrap:focus-within .hz-search{display:block}}" +
    // Hero + 分类 tile
    ".hz-hero{padding:72px 0;border-bottom:1px solid var(--hz-line);background:var(--hz-soft)}" +
    ".hz-hero-in{max-width:1280px;margin:0 auto;padding:0 32px}" +
    ".hz-eyebrow{font-size:12px;letter-spacing:.16em;text-transform:uppercase;color:var(--hz-mut);margin-bottom:18px}" +
    ".hz-hero-h{font-size:clamp(36px,5.2vw,64px);line-height:1.04;letter-spacing:-.02em;font-weight:800;margin:0 0 18px}" +
    ".hz-hero-p{font-size:17px;color:var(--hz-mut);max-width:520px;margin:0 0 28px;line-height:1.6}" +
    ".hz-hero-cta{display:flex;gap:10px;flex-wrap:wrap}" +
    ".hz-section{max-width:1280px;margin:0 auto;padding:48px 32px}" +
    ".hz-section-head{display:flex;align-items:flex-end;justify-content:space-between;margin-bottom:24px;border-bottom:1px solid var(--hz-line);padding-bottom:14px}" +
    ".hz-section-head h2{font-size:24px;letter-spacing:-.01em;font-weight:800;margin:0}.hz-section-sub{color:var(--hz-mut);font-size:13px}" +
    ".hz-tiles{display:grid;grid-template-columns:repeat(5,1fr);gap:16px}@media(max-width:1000px){.hz-tiles{grid-template-columns:repeat(3,1fr)}}@media(max-width:640px){.hz-tiles{grid-template-columns:repeat(2,1fr)}}" +
    ".hz-tile{border:none;background:none;padding:0;text-align:left;cursor:pointer;color:var(--hz-ink)}" +
    ".hz-tile-img{aspect-ratio:4/3;background:var(--hz-soft);overflow:hidden;margin-bottom:12px;display:flex;align-items:center;justify-content:center}.hz-tile-img img{width:100%;height:100%;object-fit:cover;transition:transform .3s}.hz-tile:hover .hz-tile-img img{transform:scale(1.03)}" +
    ".hz-tile-t{font-size:15px;font-weight:600}.hz-tile-s{font-size:12px;color:var(--hz-mut);margin-top:2px}" +
    // 列表筛选
    ".hz-crumb{font-size:12px;letter-spacing:.06em;text-transform:uppercase;color:var(--hz-mut);margin-bottom:8px}.hz-crumb a{cursor:pointer;color:var(--hz-mut)}.hz-crumb a:hover{color:var(--hz-ink)}" +
    ".hz-filters{display:flex;align-items:center;justify-content:space-between;gap:16px;margin-bottom:24px;min-height:34px}" +
    ".hz-chips{display:flex;gap:8px;flex-wrap:wrap}" +
    ".hz-chip{border:1px solid var(--hz-line);background:#fff;border-radius:999px;padding:7px 14px;font-size:13px;cursor:pointer;color:var(--hz-mut);white-space:nowrap}.hz-chip:hover{border-color:var(--hz-ink);color:var(--hz-ink)}" +
    ".hz-chip-on{background:var(--hz-ink);color:#fff;border-color:var(--hz-ink)}" +
    ".hz-sort{border:none;background:none;font-size:13px;color:var(--hz-mut);cursor:pointer;font-family:inherit;padding:6px 0;margin-left:auto}.hz-sort:hover{color:var(--hz-ink)}" +
    // 商品卡
    ".hz-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:28px 24px}" +
    "@media(max-width:1000px){.hz-grid{grid-template-columns:repeat(3,1fr)}}@media(max-width:640px){.hz-grid{grid-template-columns:repeat(2,1fr);gap:20px 14px}}" +
    ".hz-card{display:flex;flex-direction:column;cursor:pointer}" +
    ".hz-thumb{position:relative;overflow:hidden;aspect-ratio:1/1;background:var(--hz-soft);display:flex;align-items:center;justify-content:center;margin-bottom:14px;transition:background .2s}.hz-card:hover .hz-thumb{background:#eceae6}" +
    ".hz-ico{font-size:11px;letter-spacing:.1em;text-transform:uppercase;color:#b5b5b5}.hz-img{position:absolute;inset:0;width:100%;height:100%;object-fit:cover;background:#fff}" +
    ".hz-cat{font-size:11px;letter-spacing:.1em;text-transform:uppercase;color:var(--hz-mut);margin-bottom:6px}" +
    ".hz-name{font-size:15px;font-weight:600;line-height:1.35;margin:0 0 10px;min-height:40px}" +
    ".hz-cardbot{display:flex;align-items:center;justify-content:space-between;margin-bottom:14px}" +
    ".hz-price{font-size:16px;font-weight:700}" +
    ".hz-ok{font-size:11px;color:#4b7a3f;letter-spacing:.04em}.hz-low{font-size:11px;color:#a86b1a}.hz-oos{font-size:11px;color:#b42318}" +
    ".hz-more{text-align:center;margin-top:40px}.hz-loading{color:var(--hz-mut);text-align:center;padding:48px 0;font-size:14px;grid-column:1/-1}" +
    // PDP
    ".hz-pdp{max-width:1280px;margin:0 auto;padding:28px 32px 72px}" +
    ".hz-pdp-grid{display:grid;grid-template-columns:1fr 1fr;gap:56px;align-items:start}@media(max-width:900px){.hz-pdp-grid{grid-template-columns:1fr;gap:28px}}" +
    ".hz-pdp-frame{position:relative;aspect-ratio:1/1;background:var(--hz-soft);display:flex;align-items:center;justify-content:center;overflow:hidden}" +
    ".hz-pdp-img{position:absolute;inset:0;width:100%;height:100%;object-fit:cover;background:#fff}" +
    ".hz-pdp-brand{font-size:12px;letter-spacing:.14em;text-transform:uppercase;color:var(--hz-mut);margin-bottom:12px}" +
    ".hz-pdp-name{font-size:34px;line-height:1.08;letter-spacing:-.02em;font-weight:800;margin:0 0 18px}" +
    ".hz-pdp-price{font-size:28px;font-weight:800;margin-bottom:12px}.hz-pdp-stock{margin-bottom:26px;font-size:13px}" +
    ".hz-pdp-qtyrow{display:flex;align-items:center;gap:20px;margin-bottom:22px;font-size:12px;letter-spacing:.1em;text-transform:uppercase;color:var(--hz-mut)}" +
    ".hz-qsel{display:flex;align-items:center;border:1px solid var(--hz-line)}.hz-qsel button{width:40px;height:40px;border:none;background:#fff;font-size:18px;cursor:pointer}.hz-qsel button:hover{background:var(--hz-soft)}.hz-qsel #hz-qty{min-width:46px;text-align:center;font-size:15px;color:var(--hz-ink)}" +
    ".hz-pdp-actions{display:flex;gap:12px;margin-bottom:16px}.hz-pdp-actions .hz-btn{flex:1;padding:15px}" +
    ".hz-pdp-ask{margin-bottom:30px}.hz-pdp-ask button{display:inline-flex;align-items:center;gap:8px;background:none;border:none;color:var(--hz-mut);cursor:pointer;font-size:13px;padding:0}.hz-pdp-ask button:hover{color:var(--hz-ink);text-decoration:underline}" +
    ".hz-pdp-desc{border-top:1px solid var(--hz-line);padding-top:24px}.hz-pdp-desc h3{font-size:13px;letter-spacing:.1em;text-transform:uppercase;margin:0 0 12px}.hz-pdp-desc p{color:var(--hz-mut);line-height:1.7;font-size:14px;margin:0 0 18px}" +
    ".hz-spec{width:100%;border-collapse:collapse;font-size:14px}.hz-spec td{padding:10px 0;border-bottom:1px solid var(--hz-line)}.hz-spec td:first-child{color:var(--hz-mut);width:40%;text-transform:uppercase;font-size:12px;letter-spacing:.06em}" +
    ".hz-pdp-rel{margin-top:56px;padding-top:48px;border-top:1px solid var(--hz-line)}.hz-pdp-rel h2{font-size:22px;font-weight:800;margin:0 0 24px}" +
    ".hz-pdp-load{text-align:center;padding:120px 0;color:var(--hz-mut)}" +
    // 页脚
    ".hz-foot{border-top:1px solid var(--hz-line);background:var(--hz-soft)}" +
    ".hz-foot-in{max-width:1280px;margin:0 auto;padding:56px 32px 40px;display:grid;grid-template-columns:1.6fr 1fr 1fr 1fr;gap:32px}@media(max-width:860px){.hz-foot-in{grid-template-columns:1fr 1fr}}" +
    ".hz-foot-col{display:flex;flex-direction:column;align-items:flex-start;gap:4px}.hz-foot-col h4{font-size:12px;letter-spacing:.12em;text-transform:uppercase;margin:0 0 10px}" +
    ".hz-foot-col button,.hz-foot-col a{border:none;background:none;padding:4px 0;font-size:14px;color:var(--hz-mut);cursor:pointer;text-align:left;text-decoration:none}.hz-foot-col button:hover,.hz-foot-col a:hover{color:var(--hz-ink)}" +
    ".hz-foot-brand{font-weight:800;letter-spacing:.18em;margin-bottom:10px}.hz-foot-brandcol p{color:var(--hz-mut);font-size:13px;line-height:1.6;max-width:300px;margin:0}" +
    ".hz-foot-bottom{max-width:1280px;margin:0 auto;padding:18px 32px 32px;border-top:1px solid var(--hz-line);font-size:12px;color:#a3a3a3}" +
    // 按钮
    ".hz-btn{border:1px solid var(--hz-ink);cursor:pointer;font-size:12px;letter-spacing:.1em;text-transform:uppercase;padding:13px 22px;border-radius:0;transition:.15s}" +
    ".hz-btn-dark{background:var(--hz-ink);color:#fff}.hz-btn-dark:hover{opacity:.85}" +
    ".hz-btn-line{background:#fff;color:var(--hz-ink)}.hz-btn-line:hover{background:var(--hz-ink);color:#fff}" +
    ".hz-add{width:100%;margin-top:auto;padding:11px}" +
    // 购物车弹层
    "#hz-modal-ov{display:none;position:fixed;inset:0;background:rgba(23,23,23,.5);z-index:99999;align-items:center;justify-content:center;font-family:'Helvetica Neue',Helvetica,system-ui,sans-serif}" +
    ".hz-modal{background:#fff;width:min(640px,94vw);max-height:84vh;display:flex;flex-direction:column;overflow:hidden}" +
    ".hz-modal-head{display:flex;align-items:center;justify-content:space-between;padding:18px 22px;border-bottom:1px solid var(--hz-line)}" +
    ".hz-modal-title{font-weight:700;letter-spacing:.14em;text-transform:uppercase;font-size:13px}.hz-modal-close{border:none;background:none;cursor:pointer;color:var(--hz-ink);display:flex}" +
    ".hz-modal-body{padding:22px;overflow-y:auto;flex:1;background:#fff}" +
    ".hz-crow{display:flex;align-items:center;gap:14px;padding:16px 4px;border-bottom:1px solid var(--hz-line)}" +
    ".hz-cico{width:56px;height:56px;background:var(--hz-soft);overflow:hidden;flex:none}.hz-cico img{width:100%;height:100%;object-fit:cover}" +
    ".hz-cinfo{flex:1}.hz-cname{font-weight:600;font-size:14px}.hz-cprice{color:var(--hz-mut);font-size:13px;margin-top:3px}" +
    ".hz-cqty{display:flex;align-items:center;gap:10px}.hz-qbtn{width:28px;height:28px;border:1px solid var(--hz-line);background:#fff;cursor:pointer;font-size:16px}" +
    ".hz-cdel{background:none;border:none;color:var(--hz-mut);cursor:pointer;font-size:12px;text-transform:uppercase;letter-spacing:.08em}.hz-cdel:hover{color:var(--hz-ink)}" +
    ".hz-cfoot{display:flex;align-items:center;justify-content:space-between;margin-top:22px}.hz-ctotal{font-size:14px;text-transform:uppercase;letter-spacing:.08em}.hz-ctotal b{font-size:22px;margin-left:8px}" +
    ".hz-done{text-align:center;padding:40px 10px}.hz-done-ico{width:64px;height:64px;border-radius:50%;background:var(--hz-ink);color:#fff;font-size:32px;display:flex;align-items:center;justify-content:center;margin:0 auto 18px}.hz-done h2{font-size:24px;margin:0 0 10px}.hz-done p{color:var(--hz-mut);line-height:1.7;margin-bottom:24px}" +
    ".hz-toast{position:fixed;bottom:40px;left:50%;transform:translateX(-50%) translateY(20px);background:var(--hz-ink);color:#fff;padding:12px 20px;font-size:13px;letter-spacing:.04em;z-index:100000;opacity:0;transition:.3s}.hz-toast.show{opacity:1;transform:translateX(-50%) translateY(0)}" +
    // 助手：悬浮入口 + 右侧抽屉
    ".hz-cs-fab{position:fixed;right:24px;bottom:24px;z-index:9500;height:48px;padding:0 18px 0 14px;border-radius:24px;border:none;background:var(--hz-ink);color:#fff;font-size:13px;letter-spacing:.02em;cursor:pointer;display:inline-flex;align-items:center;gap:9px;box-shadow:0 8px 24px rgba(0,0,0,.22);transition:.15s}.hz-cs-fab:hover{transform:translateY(-1px)}" +
    "html.hz-dr-open .hz-cs-fab{opacity:0;pointer-events:none}" +
    "#hz-drawer{position:fixed;inset:0;z-index:99990;pointer-events:none;font-family:'Helvetica Neue',Helvetica,system-ui,sans-serif}" +
    ".hz-dr-scrim{position:absolute;inset:0;background:rgba(23,23,23,.28);opacity:0;transition:.25s}" +
    ".hz-dr{position:absolute;top:0;right:0;bottom:0;width:min(420px,100vw);background:#fff;display:flex;flex-direction:column;transform:translateX(100%);transition:transform .28s cubic-bezier(.2,.7,.2,1);box-shadow:-24px 0 48px -32px rgba(0,0,0,.35)}" +
    "#hz-drawer.open{pointer-events:auto}#hz-drawer.open .hz-dr-scrim{opacity:1}#hz-drawer.open .hz-dr{transform:none}" +
    ".hz-dr-head{display:flex;align-items:flex-start;justify-content:space-between;padding:20px 22px 16px;border-bottom:1px solid var(--hz-line)}" +
    ".hz-dr-title{font-weight:700;letter-spacing:.14em;text-transform:uppercase;font-size:13px}.hz-dr-sub{font-size:12px;color:var(--hz-mut);margin-top:4px}" +
    ".hz-dr-x{border:none;background:none;cursor:pointer;color:var(--hz-ink);display:flex;padding:2px}" +
    ".hz-dr-body{flex:1;overflow-y:auto;padding:20px 22px;display:flex;flex-direction:column}" +
    ".hz-bubble{padding:11px 14px;margin:5px 0;max-width:88%;white-space:pre-wrap;word-break:break-word;font-size:14px;line-height:1.6}" +
    ".hz-user{background:var(--hz-ink);color:#fff;align-self:flex-end}.hz-assistant{background:var(--hz-soft);color:var(--hz-ink);align-self:flex-start}.hz-thinking{color:var(--hz-mut)}" +
    ".hz-dr-sugg{display:flex;flex-wrap:wrap;gap:8px;padding:0 22px 12px}.hz-dr-sugg button{border:1px solid var(--hz-line);background:#fff;border-radius:999px;padding:7px 12px;font-size:12px;color:var(--hz-mut);cursor:pointer;text-align:left}.hz-dr-sugg button:hover{border-color:var(--hz-ink);color:var(--hz-ink)}" +
    ".hz-dr-foot{display:flex;gap:8px;padding:14px 22px 20px;border-top:1px solid var(--hz-line)}" +
    ".hz-dr-input{flex:1;padding:12px;border:1px solid var(--hz-line);font-size:14px;outline:none;font-family:inherit}.hz-dr-input:focus{border-color:var(--hz-ink)}" +
    ".hz-dr-send{padding:0 18px;background:var(--hz-ink);color:#fff;border:none;cursor:pointer;font-size:12px;letter-spacing:.1em;text-transform:uppercase;font-family:inherit}" +
    "";
  document.head.appendChild(css);

  toggleShop();
  // 监听 SPA 路由变化
  var _ps = history.pushState; history.pushState = function () { _ps.apply(this, arguments); setTimeout(toggleShop, 50); };
  window.addEventListener("popstate", function () { setTimeout(toggleShop, 50); });
  setInterval(toggleShop, 600);
})();
