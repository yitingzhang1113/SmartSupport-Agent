/*
 * SmartShop 商城交互层(注入)。/ecommerce 上渲染一个自建的 Horizon 风格商城(盖住 mock),
 * 数据来自 /api/products(Business_data)。含:分类浏览、商品详情、购物车+结算、常驻 AI 客服。
 * 设计参考 Shopify Horizon:中性黑白灰、大留白、大字体、极简按钮、无重阴影。
 */
(function () {
  "use strict";

  var BASE = "http://localhost:8010";
  var API_PRODUCTS = BASE + "/api/products";
  var API_DETAIL = BASE + "/api/products/detail";
  var API_CATS = BASE + "/api/categories";
  var API_CHAT = BASE + "/api/langgraph/query";
  var PAGE = 12;

  var ICON = {
    "Smart Speaker": "🔊", "Smart Display": "🖥️", "Smart Thermostat": "🌡️", "Smart Doorbell": "🔔",
    "Smart Camera": "📷", "Smart Lock": "🔒", "Smart Plug": "🔌", "Smart Lighting": "💡",
    "Robot Vacuum": "🤖", "Air Purifier": "🌀", "Security System": "🛡️", "Streaming Device": "📡",
    "Smart TV": "📺", "Home Hub": "🏠", "Smart Sensor": "📶"
  };
  function icon(c) { return ICON[c] || "📦"; }
  function thumb(p, big) {
    var ic = '<span class="hz-ico">' + icon(p.category) + "</span>";
    if (p.image) return ic + '<img class="hz-img" src="' + BASE + esc(p.image) + '" alt="" onerror="this.remove()">';
    return ic;
  }
  function esc(s) {
    return String(s == null ? "" : s).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  }
  function money(n) { return "¥" + (Number(n) || 0).toLocaleString("zh-CN", { minimumFractionDigits: 2, maximumFractionDigits: 2 }); }
  function stockText(s) {
    if (s <= 0) return '<span class="hz-oos">Sold out</span>';
    if (s < 20) return '<span class="hz-low">Low · ' + s + "</span>";
    return '<span class="hz-ok">In stock</span>';
  }

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
  function setChip(cat) {
    if (!shop) return;
    shop.querySelectorAll(".hz-chip").forEach(function (x) {
      x.classList.toggle("hz-chip-on", (x.getAttribute("data-cat") || "") === (cat || ""));
    });
  }
  function syncBadges() {
    var n = cartCount();
    document.querySelectorAll(".hz-cartcount").forEach(function (el) { el.textContent = n; el.style.display = n ? "flex" : "none"; });
  }

  function toast(msg) {
    var t = document.createElement("div"); t.className = "hz-toast"; t.textContent = msg;
    document.body.appendChild(t);
    setTimeout(function () { t.classList.add("show"); }, 10);
    setTimeout(function () { t.classList.remove("show"); setTimeout(function () { t.remove(); }, 300); }, 1700);
  }

  // ================= 弹层 =================
  var overlay, titleEl, bodyEl, footEl, inputEl;
  function ensureModal() {
    if (overlay) return;
    overlay = document.createElement("div"); overlay.id = "hz-modal-ov";
    overlay.innerHTML =
      '<div class="hz-modal"><div class="hz-modal-head"><span class="hz-modal-title"></span><span class="hz-modal-close">&times;</span></div>' +
      '<div class="hz-modal-body"></div>' +
      '<div class="hz-modal-foot"><input class="hz-modal-input" type="text" placeholder="Ask about products, orders, returns…"/><button class="hz-modal-send">Send</button></div></div>';
    document.body.appendChild(overlay);
    titleEl = overlay.querySelector(".hz-modal-title"); bodyEl = overlay.querySelector(".hz-modal-body");
    footEl = overlay.querySelector(".hz-modal-foot"); inputEl = overlay.querySelector(".hz-modal-input");
    overlay.querySelector(".hz-modal-close").addEventListener("click", hide);
    overlay.addEventListener("click", function (e) { if (e.target === overlay) hide(); });
    overlay.querySelector(".hz-modal-send").addEventListener("click", sendChat);
    inputEl.addEventListener("keydown", function (e) { if (e.key === "Enter") sendChat(); });
  }
  function openModal(title, mode) { ensureModal(); titleEl.textContent = title; footEl.style.display = mode === "chat" ? "flex" : "none"; overlay.style.display = "flex"; }
  function hide() { if (overlay) overlay.style.display = "none"; }

  // ---------- 商品详情 ----------
  function showDetail(name) {
    openModal("Product", "browse");
    bodyEl.innerHTML = '<div class="hz-loading">Loading…</div>';
    fetch(API_DETAIL + "?name=" + encodeURIComponent(name)).then(function (r) { if (!r.ok) throw 0; return r.json(); })
      .then(function (p) {
        bodyEl.innerHTML =
          '<div class="hz-detail"><div class="hz-d-hero">' + thumb(p) + "</div>" +
          '<div class="hz-d-cat">' + esc(p.category) + " · " + esc(p.supplier) + "</div>" +
          '<h2 class="hz-d-name">' + esc(p.name) + "</h2>" +
          '<div class="hz-d-price">' + money(p.price) + "</div>" +
          '<div class="hz-d-meta">' + stockText(p.stock) + (p.quantityPerUnit ? ' &nbsp;·&nbsp; ' + esc(p.quantityPerUnit) : "") + "</div>" +
          '<div class="hz-d-actions">' +
          '<button class="hz-btn hz-btn-dark" data-act="cart" data-name="' + esc(p.name) + '" data-price="' + p.price + '" data-cat="' + esc(p.category) + '">Add to cart</button>' +
          '<button class="hz-btn hz-btn-line" data-act="ask" data-name="' + esc(p.name) + '">Ask about this</button></div></div>';
      }).catch(function () { bodyEl.innerHTML = '<div class="hz-loading">Not found</div>'; });
  }

  // ---------- 购物车弹层 ----------
  function openCart() {
    openModal("Your cart", "browse");
    if (!cart.length) { bodyEl.innerHTML = '<div class="hz-loading">Your cart is empty.</div>'; return; }
    var h = '<div class="hz-cart">';
    cart.forEach(function (it, i) {
      h += '<div class="hz-crow"><div class="hz-cico">' + icon(it.category) + "</div>" +
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

  // ================= 客服 =================
  function openChat(greeting) {
    openModal("SmartSupport", "chat");
    if (!bodyEl.dataset.chat) { bodyEl.innerHTML = ""; bodyEl.dataset.chat = "1"; bubble("assistant", greeting || "Hi! I can help with products, orders and returns. What can I do for you?"); }
  }
  function bubble(role, text) { var b = document.createElement("div"); b.className = "hz-bubble hz-" + role; b.textContent = text; bodyEl.appendChild(b); bodyEl.scrollTop = bodyEl.scrollHeight; return b; }
  function sendChat() { var q = (inputEl.value || "").trim(); if (!q) return; inputEl.value = ""; askAgent(q); }
  function askAgent(question) {
    if (!bodyEl.dataset.chat) { bodyEl.innerHTML = ""; bodyEl.dataset.chat = "1"; }
    bubble("user", question); var ans = bubble("assistant", "Thinking…"); var acc = "";
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
            if (acc.trim()) ans.textContent = acc; bodyEl.scrollTop = bodyEl.scrollHeight;
          }
          return pump();
        });
      }
      return pump();
    }).then(function () { if (!acc.trim()) ans.textContent = "(no response)"; })
      .catch(function (err) { ans.textContent = "Sorry, an error occurred: " + err.message; });
  }

  var CN2EN = { "智能音箱": "Smart Speaker", "音箱": "Smart Speaker", "智能显示器": "Smart Display", "智能屏": "Smart Display", "恒温器": "Smart Thermostat", "智能门铃": "Smart Doorbell", "门铃": "Smart Doorbell", "智能摄像头": "Smart Camera", "摄像头": "Smart Camera", "摄像机": "Smart Camera", "智能门锁": "Smart Lock", "门锁": "Smart Lock", "锁": "Smart Lock", "智能插座": "Smart Plug", "插座": "Smart Plug", "智能照明": "Smart Lighting", "智能灯": "Smart Lighting", "灯": "Smart Lighting", "扫地机器人": "Robot Vacuum", "扫地机": "Robot Vacuum", "吸尘器": "Robot Vacuum", "空气净化器": "Air Purifier", "净化器": "Air Purifier", "安防": "Security System", "流媒体": "Streaming Device", "智能电视": "Smart TV", "电视": "Smart TV", "家庭中枢": "Home Hub", "传感器": "Smart Sensor" };
  function toEn(q) { if (!q) return null; if (CN2EN[q]) return CN2EN[q]; var k = Object.keys(CN2EN).sort(function (a, b) { return b.length - a.length; }); for (var i = 0; i < k.length; i++) if (q.indexOf(k[i]) >= 0) return CN2EN[k[i]]; return null; }

  // ================= Horizon 商城页 =================
  var shop, gridEl, gridInfo, moreWrap, state = { items: [], shown: 0, title: "" };
  function buildShop() {
    if (shop) return;
    shop = document.createElement("div"); shop.id = "hz-shop";
    shop.innerHTML =
      '<div class="hz-announce">Free shipping over ¥999 · Smart home, beautifully simple</div>' +
      '<header class="hz-head"><div class="hz-brand">SMARTSHOP</div>' +
      '<div class="hz-searchwrap"><input class="hz-search" type="text" placeholder="Search products"/><button class="hz-search-btn" data-hz="search">Search</button></div>' +
      '<div class="hz-actions"><button class="hz-iconbtn" data-hz="cart">Cart<span class="hz-cartcount">0</span></button>' +
      '<button class="hz-iconbtn hz-cs" data-hz="cs">Support</button></div></header>' +
      '<nav class="hz-cats" id="hz-cats"></nav>' +
      '<main id="hz-main"></main>';
    document.body.appendChild(shop);
    // 分类
    fetch(API_CATS).then(function (r) { return r.json(); }).then(function (d) {
      var cats = (d && d.items) || []; var nav = shop.querySelector("#hz-cats");
      var html = '<button class="hz-chip hz-chip-on" data-cat="">All</button>';
      cats.forEach(function (c) { html += '<button class="hz-chip" data-cat="' + esc(c.name) + '">' + icon(c.name) + " " + esc(c.name) + "</button>"; });
      nav.innerHTML = html;
    });
    renderHome();
    syncBadges();
  }

  var HOME_HTML =
    '<section class="hz-hero"><div class="hz-hero-in"><div class="hz-eyebrow">New in · Smart home</div>' +
    '<h1 class="hz-hero-h">Your home,<br>beautifully connected.</h1>' +
    '<p class="hz-hero-p">Locks, cameras, lighting and more — curated devices that just work together.</p>' +
    '<button class="hz-btn hz-btn-dark" data-hz="shopall">Shop all products</button></div></section>' +
    '<section class="hz-section"><div class="hz-section-head"><h2 id="hz-grid-title">Featured</h2><span class="hz-section-sub" id="hz-grid-info"></span></div>' +
    '<div class="hz-grid" id="hz-grid"></div><div class="hz-more" id="hz-more"></div></section>' +
    '<footer class="hz-foot"><div class="hz-foot-brand">SMARTSHOP</div><div class="hz-foot-note">Powered by SmartSupport · Demo storefront over Business_data</div></footer>';

  function renderHome() {
    var main = shop.querySelector("#hz-main"); main.innerHTML = HOME_HTML;
    gridEl = main.querySelector("#hz-grid"); gridInfo = main.querySelector("#hz-grid-info"); moreWrap = main.querySelector("#hz-more");
    if (state.items && state.items.length) {
      main.querySelector("#hz-grid-title").textContent = state.title || "Featured";
      gridInfo.textContent = state.items.length + " products"; renderGrid();
    } else loadGrid("Featured", "limit=200");
  }
  function goHome() { if (shop && !shop.querySelector("#hz-grid")) renderHome(); }

  function loadGrid(title, params) {
    shop.querySelector("#hz-grid-title").textContent = title;
    gridEl.innerHTML = '<div class="hz-loading">Loading…</div>'; moreWrap.innerHTML = "";
    fetch(API_PRODUCTS + "?" + params + "&limit=200").then(function (r) { return r.json(); }).then(function (d) {
      var items = (d && d.items) || [];
      state = { items: items, shown: Math.min(PAGE, items.length), title: title };
      gridInfo.textContent = items.length + " products";
      renderGrid();
    }).catch(function () { gridEl.innerHTML = '<div class="hz-loading">Failed to load</div>'; });
  }
  function renderGrid() {
    if (!state.items.length) { gridEl.innerHTML = '<div class="hz-loading">No products</div>'; moreWrap.innerHTML = ""; return; }
    var html = "";
    state.items.slice(0, state.shown).forEach(function (p) {
      html += '<article class="hz-card" data-name="' + esc(p.name) + '">' +
        '<div class="hz-thumb">' + thumb(p) + "</div>" +
        '<div class="hz-cat">' + esc(p.category) + "</div>" +
        '<h3 class="hz-name">' + esc(p.name) + "</h3>" +
        '<div class="hz-cardbot"><span class="hz-price">' + money(p.price) + "</span>" + stockText(p.stock) + "</div>" +
        '<button class="hz-btn hz-btn-line hz-add" data-act="cart" data-name="' + esc(p.name) + '" data-price="' + p.price + '" data-cat="' + esc(p.category) + '">Add to cart</button></article>';
    });
    gridEl.innerHTML = html;
    moreWrap.innerHTML = state.shown < state.items.length ? '<button class="hz-btn hz-btn-line" data-hz="more">Load more (' + (state.items.length - state.shown) + ")</button>" : "";
  }

  // ---------- 商品详情页(PDP)----------
  function renderPDP(name) {
    if (!shop) buildShop();
    var main = shop.querySelector("#hz-main");
    shop.scrollTop = 0; main.innerHTML = '<div class="hz-pdp-load">Loading…</div>';
    fetch(API_DETAIL + "?name=" + encodeURIComponent(name)).then(function (r) { if (!r.ok) throw 0; return r.json(); })
      .then(function (p) {
        fetch(API_PRODUCTS + "?category=" + encodeURIComponent(p.category) + "&limit=6").then(function (r) { return r.json(); })
          .then(function (rel) {
            var related = ((rel && rel.items) || []).filter(function (x) { return x.name !== p.name; }).slice(0, 4);
            main.innerHTML = pdpHTML(p, related); shop.scrollTop = 0;
          }).catch(function () { main.innerHTML = pdpHTML(p, []); });
      }).catch(function () { main.innerHTML = '<div class="hz-pdp-load">Product not found</div>'; });
  }
  function pdpHTML(p, related) {
    var img = p.image ? '<img class="hz-pdp-img" src="' + BASE + esc(p.image) + '" alt="" onerror="this.style.display=\'none\'">' : "";
    var stockLine = p.stock > 0 ? '<span class="hz-ok">In stock · ' + p.stock + " available</span>" : '<span class="hz-oos">Sold out</span>';
    var rel = "";
    if (related.length) {
      rel = '<div class="hz-pdp-rel"><h2>You may also like</h2><div class="hz-grid">';
      related.forEach(function (r) {
        rel += '<article class="hz-card hz-rel" data-name="' + esc(r.name) + '"><div class="hz-thumb">' + thumb(r) + '</div><div class="hz-cat">' + esc(r.category) + '</div><h3 class="hz-name">' + esc(r.name) + '</h3><div class="hz-cardbot"><span class="hz-price">' + money(r.price) + "</span>" + stockText(r.stock) + "</div></article>";
      });
      rel += "</div></div>";
    }
    return '<div class="hz-pdp">' +
      '<div class="hz-crumb"><a data-pdp="back">Home</a> &nbsp;/&nbsp; <span>' + esc(p.category) + '</span> &nbsp;/&nbsp; <span>' + esc(p.name) + "</span></div>" +
      '<div class="hz-pdp-grid">' +
      '<div class="hz-pdp-frame"><span class="hz-pdp-ico">' + icon(p.category) + "</span>" + img + "</div>" +
      '<div class="hz-pdp-info">' +
      '<div class="hz-pdp-brand">' + esc(p.supplier) + "</div>" +
      '<h1 class="hz-pdp-name">' + esc(p.name) + "</h1>" +
      '<div class="hz-pdp-price">' + money(p.price) + "</div>" +
      '<div class="hz-pdp-stock">' + stockLine + "</div>" +
      '<div class="hz-pdp-qtyrow"><span>Quantity</span><div class="hz-qsel"><button data-pdp="qminus">−</button><span id="hz-qty">1</span><button data-pdp="qplus">+</button></div></div>' +
      '<div class="hz-pdp-actions">' +
      '<button class="hz-btn hz-btn-dark" data-pdp="addcart" data-name="' + esc(p.name) + '" data-price="' + p.price + '" data-cat="' + esc(p.category) + '">Add to cart</button>' +
      '<button class="hz-btn hz-btn-line" data-pdp="buynow" data-name="' + esc(p.name) + '" data-price="' + p.price + '" data-cat="' + esc(p.category) + '">Buy it now</button></div>' +
      '<div class="hz-pdp-ask"><button data-act="ask" data-name="' + esc(p.name) + '">💬 Ask SmartSupport about this product</button></div>' +
      '<div class="hz-pdp-desc"><h3>Details</h3><p>' + esc(p.name) + " by " + esc(p.supplier) + " — part of our " + esc(p.category) + " collection. Packaged as " + esc(p.quantityPerUnit || "standard unit") + ".</p>" +
      '<table class="hz-spec"><tr><td>Category</td><td>' + esc(p.category) + "</td></tr><tr><td>Brand</td><td>" + esc(p.supplier) + "</td></tr><tr><td>Packaging</td><td>" + esc(p.quantityPerUnit || "—") + "</td></tr><tr><td>Availability</td><td>" + (p.stock > 0 ? p.stock + " in stock" : "Sold out") + "</td></tr><tr><td>SKU</td><td>#" + esc(p.id) + "</td></tr></table></div>" +
      "</div></div>" + rel + "</div>";
  }

  function onShop() { return location.pathname.indexOf("/ecommerce") === 0; }
  function toggleShop() {
    if (onShop()) { buildShop(); shop.style.display = "block"; document.documentElement.classList.add("hz-lock"); }
    else if (shop) { shop.style.display = "none"; document.documentElement.classList.remove("hz-lock"); }
  }

  // ================= 事件 =================
  document.addEventListener("click", function (e) {
    var t = e.target; if (!t || !t.closest) return;

    var cc = t.closest("[data-cart]");
    if (cc) {
      e.preventDefault(); var a = cc.getAttribute("data-cart"), i = parseInt(cc.getAttribute("data-i"), 10);
      if (a === "inc") { cart[i].qty++; saveCart(cart); openCart(); }
      else if (a === "dec") { cart[i].qty--; if (cart[i].qty <= 0) cart.splice(i, 1); saveCart(cart); openCart(); }
      else if (a === "del") { cart.splice(i, 1); saveCart(cart); openCart(); }
      else if (a === "checkout") checkout(); else if (a === "close") hide();
      return;
    }
    var pdp = t.closest("[data-pdp]");
    if (pdp) {
      e.preventDefault(); var pk = pdp.getAttribute("data-pdp");
      if (pk === "back") { goHome(); shop.scrollTop = 0; }
      else if (pk === "qminus" || pk === "qplus") {
        var qel = document.getElementById("hz-qty"); var v = parseInt(qel.textContent, 10) || 1;
        v += pk === "qplus" ? 1 : -1; if (v < 1) v = 1; qel.textContent = v;
      } else if (pk === "addcart" || pk === "buynow") {
        var qe = document.getElementById("hz-qty"); var n = parseInt(qe ? qe.textContent : "1", 10) || 1;
        addToCart(pdp.getAttribute("data-name"), pdp.getAttribute("data-price"), pdp.getAttribute("data-cat"), n);
        if (pk === "buynow") openCart();
      }
      return;
    }
    var hz = t.closest("[data-hz]");
    if (hz) {
      e.preventDefault(); var k = hz.getAttribute("data-hz");
      if (k === "cart") openCart();
      else if (k === "cs") openChat();
      else if (k === "shopall") { setChip(""); goHome(); loadGrid("All products", "limit=200"); }
      else if (k === "more") { state.shown += PAGE; renderGrid(); }
      else if (k === "search") { var q = shop.querySelector(".hz-search").value.trim(); var en = q ? toEn(q) : null; goHome(); loadGrid(q ? "Search · " + q : "All products", q ? "q=" + encodeURIComponent(en || q) : "limit=200"); }
      return;
    }
    var chip = t.closest(".hz-chip");
    if (chip) {
      e.preventDefault();
      shop.querySelectorAll(".hz-chip").forEach(function (x) { x.classList.remove("hz-chip-on"); });
      chip.classList.add("hz-chip-on");
      var cat = chip.getAttribute("data-cat");
      goHome();
      loadGrid(cat || "All products", cat ? "category=" + encodeURIComponent(cat) : "limit=200");
      return;
    }
    var ab = t.closest("[data-act]");
    if (ab) {
      e.preventDefault(); var an = ab.getAttribute("data-name");
      if (ab.getAttribute("data-act") === "cart") addToCart(an, ab.getAttribute("data-price"), ab.getAttribute("data-cat"));
      else if (ab.getAttribute("data-act") === "ask") { openChat(); askAgent("Tell me about " + an + " — price, stock and features."); }
      return;
    }
    var card = t.closest(".hz-card");
    if (card) { e.preventDefault(); renderPDP(card.getAttribute("data-name")); return; }
    if (t.closest(".hz-cs-fab")) { e.preventDefault(); openChat(); return; }
  }, true);

  // 客服常驻悬浮
  var fab;
  function ensureFab() {
    if (fab) return;
    fab = document.createElement("button"); fab.className = "hz-cs-fab"; fab.title = "SmartSupport";
    fab.innerHTML = "💬";
    document.body.appendChild(fab);
  }

  // ---------- 样式 ----------
  var css = document.createElement("style");
  css.textContent =
    ":root{--hz-ink:#171717;--hz-mut:#737373;--hz-line:#e7e5e4;--hz-bg:#ffffff;--hz-soft:#f5f4f2}" +
    "html.hz-lock,html.hz-lock body{overflow:auto}" +
    "#hz-shop{display:none;position:fixed;inset:0;overflow-y:auto;z-index:9000;background:var(--hz-bg);color:var(--hz-ink);font-family:'Helvetica Neue',Helvetica,system-ui,-apple-system,'Segoe UI',Arial,sans-serif;-webkit-font-smoothing:antialiased}" +
    ".hz-announce{background:var(--hz-ink);color:#fff;text-align:center;font-size:12px;letter-spacing:.08em;padding:9px 12px;text-transform:uppercase}" +
    ".hz-head{display:flex;align-items:center;gap:24px;padding:22px 40px;border-bottom:1px solid var(--hz-line);position:sticky;top:0;background:rgba(255,255,255,.92);backdrop-filter:saturate(1.2) blur(8px);z-index:5}" +
    ".hz-brand{font-weight:800;font-size:20px;letter-spacing:.18em}" +
    ".hz-searchwrap{flex:1;display:flex;max-width:520px;margin:0 auto}" +
    ".hz-search{flex:1;border:1px solid var(--hz-line);border-right:none;padding:11px 14px;font-size:14px;outline:none;border-radius:0}" +
    ".hz-search:focus{border-color:var(--hz-ink)}" +
    ".hz-search-btn{border:1px solid var(--hz-ink);background:var(--hz-ink);color:#fff;padding:0 18px;font-size:12px;letter-spacing:.1em;text-transform:uppercase;cursor:pointer}" +
    ".hz-actions{display:flex;gap:8px}" +
    ".hz-iconbtn{position:relative;border:1px solid var(--hz-line);background:#fff;padding:10px 16px;font-size:12px;letter-spacing:.1em;text-transform:uppercase;cursor:pointer}.hz-iconbtn:hover{border-color:var(--hz-ink)}" +
    ".hz-cs{background:var(--hz-ink);color:#fff;border-color:var(--hz-ink)}" +
    ".hz-cartcount{position:absolute;top:-8px;right:-8px;background:var(--hz-ink);color:#fff;font-size:11px;min-width:18px;height:18px;border-radius:9px;display:none;align-items:center;justify-content:center;padding:0 5px}" +
    ".hz-cats{display:flex;gap:10px;flex-wrap:wrap;padding:16px 40px;border-bottom:1px solid var(--hz-line)}" +
    ".hz-chip{border:1px solid var(--hz-line);background:#fff;border-radius:999px;padding:8px 15px;font-size:13px;cursor:pointer;color:var(--hz-mut);white-space:nowrap}.hz-chip:hover{border-color:var(--hz-ink);color:var(--hz-ink)}" +
    ".hz-chip-on{background:var(--hz-ink);color:#fff;border-color:var(--hz-ink)}" +
    ".hz-hero{padding:80px 40px;border-bottom:1px solid var(--hz-line);background:var(--hz-soft)}" +
    ".hz-hero-in{max-width:1200px;margin:0 auto}" +
    ".hz-eyebrow{font-size:12px;letter-spacing:.16em;text-transform:uppercase;color:var(--hz-mut);margin-bottom:20px}" +
    ".hz-hero-h{font-size:clamp(38px,6vw,76px);line-height:1.02;letter-spacing:-.02em;font-weight:800;margin:0 0 20px}" +
    ".hz-hero-p{font-size:18px;color:var(--hz-mut);max-width:520px;margin:0 0 30px;line-height:1.6}" +
    ".hz-section{max-width:1200px;margin:0 auto;padding:56px 40px}" +
    ".hz-section-head{display:flex;align-items:baseline;justify-content:space-between;margin-bottom:28px;border-bottom:1px solid var(--hz-line);padding-bottom:16px}" +
    ".hz-section-head h2{font-size:26px;letter-spacing:-.01em;font-weight:800;margin:0}.hz-section-sub{color:var(--hz-mut);font-size:13px}" +
    ".hz-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:28px 24px}" +
    "@media(max-width:1000px){.hz-grid{grid-template-columns:repeat(2,1fr)}}" +
    ".hz-card{display:flex;flex-direction:column;cursor:pointer}" +
    ".hz-thumb{position:relative;overflow:hidden;aspect-ratio:1/1;background:var(--hz-soft);display:flex;align-items:center;justify-content:center;font-size:64px;margin-bottom:14px;transition:background .2s}.hz-card:hover .hz-thumb{background:#eceae6}" +
    ".hz-ico{display:flex;align-items:center;justify-content:center;width:100%;height:100%}.hz-img{position:absolute;inset:0;width:100%;height:100%;object-fit:cover;background:#fff}" +
    ".hz-cat{font-size:11px;letter-spacing:.1em;text-transform:uppercase;color:var(--hz-mut);margin-bottom:6px}" +
    ".hz-name{font-size:15px;font-weight:600;line-height:1.35;margin:0 0 10px;min-height:40px}" +
    ".hz-cardbot{display:flex;align-items:center;justify-content:space-between;margin-bottom:14px}" +
    ".hz-price{font-size:16px;font-weight:700}" +
    ".hz-ok{font-size:11px;color:#4b7a3f;letter-spacing:.04em}.hz-low{font-size:11px;color:#a86b1a}.hz-oos{font-size:11px;color:#b42318}" +
    ".hz-more{text-align:center;margin-top:40px}" +
    // PDP 商品详情页
    ".hz-pdp{max-width:1200px;margin:0 auto;padding:28px 40px 72px}" +
    ".hz-crumb{font-size:12px;letter-spacing:.06em;text-transform:uppercase;color:var(--hz-mut);margin-bottom:30px}.hz-crumb a{cursor:pointer;color:var(--hz-mut);text-decoration:none}.hz-crumb a:hover{color:var(--hz-ink)}" +
    ".hz-pdp-grid{display:grid;grid-template-columns:1fr 1fr;gap:56px;align-items:start}@media(max-width:900px){.hz-pdp-grid{grid-template-columns:1fr;gap:28px}}" +
    ".hz-pdp-frame{position:relative;aspect-ratio:1/1;background:var(--hz-soft);display:flex;align-items:center;justify-content:center;overflow:hidden}" +
    ".hz-pdp-ico{font-size:120px}.hz-pdp-img{position:absolute;inset:0;width:100%;height:100%;object-fit:cover;background:#fff}" +
    ".hz-pdp-brand{font-size:12px;letter-spacing:.14em;text-transform:uppercase;color:var(--hz-mut);margin-bottom:12px}" +
    ".hz-pdp-name{font-size:34px;line-height:1.08;letter-spacing:-.02em;font-weight:800;margin:0 0 18px}" +
    ".hz-pdp-price{font-size:28px;font-weight:800;margin-bottom:12px}.hz-pdp-stock{margin-bottom:26px;font-size:13px}" +
    ".hz-pdp-qtyrow{display:flex;align-items:center;gap:20px;margin-bottom:22px;font-size:12px;letter-spacing:.1em;text-transform:uppercase;color:var(--hz-mut)}" +
    ".hz-qsel{display:flex;align-items:center;border:1px solid var(--hz-line)}.hz-qsel button{width:40px;height:40px;border:none;background:#fff;font-size:18px;cursor:pointer}.hz-qsel button:hover{background:var(--hz-soft)}.hz-qsel #hz-qty{min-width:46px;text-align:center;font-size:15px;color:var(--hz-ink)}" +
    ".hz-pdp-actions{display:flex;gap:12px;margin-bottom:16px}.hz-pdp-actions .hz-btn{flex:1;padding:15px}" +
    ".hz-pdp-ask{margin-bottom:30px}.hz-pdp-ask button{background:none;border:none;color:var(--hz-mut);cursor:pointer;font-size:13px;padding:0}.hz-pdp-ask button:hover{color:var(--hz-ink);text-decoration:underline}" +
    ".hz-pdp-desc{border-top:1px solid var(--hz-line);padding-top:24px}.hz-pdp-desc h3{font-size:13px;letter-spacing:.1em;text-transform:uppercase;margin:0 0 12px}.hz-pdp-desc p{color:var(--hz-mut);line-height:1.7;font-size:14px;margin:0 0 18px}" +
    ".hz-spec{width:100%;border-collapse:collapse;font-size:14px}.hz-spec td{padding:10px 0;border-bottom:1px solid var(--hz-line)}.hz-spec td:first-child{color:var(--hz-mut);width:40%;text-transform:uppercase;font-size:12px;letter-spacing:.06em}" +
    ".hz-pdp-rel{max-width:1200px;margin:56px auto 0;padding-top:48px;border-top:1px solid var(--hz-line)}.hz-pdp-rel h2{font-size:22px;font-weight:800;margin:0 0 24px}" +
    ".hz-pdp-load{text-align:center;padding:120px 0;color:var(--hz-mut)}" +
    ".hz-foot{border-top:1px solid var(--hz-line);padding:48px 40px;display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:12px}" +
    ".hz-foot-brand{font-weight:800;letter-spacing:.18em}.hz-foot-note{color:var(--hz-mut);font-size:13px}" +
    ".hz-btn{border:1px solid var(--hz-ink);cursor:pointer;font-size:12px;letter-spacing:.1em;text-transform:uppercase;padding:13px 22px;border-radius:0;transition:.15s}" +
    ".hz-btn-dark{background:var(--hz-ink);color:#fff}.hz-btn-dark:hover{opacity:.85}" +
    ".hz-btn-line{background:#fff;color:var(--hz-ink)}.hz-btn-line:hover{background:var(--hz-ink);color:#fff}" +
    ".hz-add{width:100%;margin-top:auto;padding:11px}" +
    // 弹层
    "#hz-modal-ov{display:none;position:fixed;inset:0;background:rgba(23,23,23,.5);z-index:99999;align-items:center;justify-content:center;font-family:'Helvetica Neue',Helvetica,system-ui,sans-serif}" +
    ".hz-modal{background:#fff;width:min(640px,94vw);max-height:84vh;display:flex;flex-direction:column;overflow:hidden}" +
    ".hz-modal-head{display:flex;align-items:center;justify-content:space-between;padding:18px 22px;border-bottom:1px solid var(--hz-line)}" +
    ".hz-modal-title{font-weight:700;letter-spacing:.14em;text-transform:uppercase;font-size:13px}.hz-modal-close{cursor:pointer;font-size:24px;line-height:1}" +
    ".hz-modal-body{padding:22px;overflow-y:auto;flex:1;background:#fff}" +
    ".hz-loading{color:var(--hz-mut);text-align:center;padding:48px 0;font-size:14px}" +
    ".hz-detail{text-align:center}.hz-d-hero{position:relative;overflow:hidden;height:260px;font-size:88px;background:var(--hz-soft);display:flex;align-items:center;justify-content:center;margin-bottom:20px}.hz-d-hero .hz-ico{font-size:96px}" +
    ".hz-d-cat{font-size:11px;letter-spacing:.12em;text-transform:uppercase;color:var(--hz-mut);margin-bottom:8px}" +
    ".hz-d-name{font-size:24px;font-weight:800;margin:0 0 12px;letter-spacing:-.01em}" +
    ".hz-d-price{font-size:26px;font-weight:800;margin-bottom:10px}.hz-d-meta{color:var(--hz-mut);font-size:13px;margin-bottom:24px}" +
    ".hz-d-actions{display:flex;gap:12px;justify-content:center}" +
    ".hz-cart{border-top:1px solid var(--hz-line)}" +
    ".hz-crow{display:flex;align-items:center;gap:14px;padding:16px 4px;border-bottom:1px solid var(--hz-line)}" +
    ".hz-cico{font-size:30px;width:52px;height:52px;background:var(--hz-soft);display:flex;align-items:center;justify-content:center}" +
    ".hz-cinfo{flex:1}.hz-cname{font-weight:600;font-size:14px}.hz-cprice{color:var(--hz-mut);font-size:13px;margin-top:3px}" +
    ".hz-cqty{display:flex;align-items:center;gap:10px}.hz-qbtn{width:28px;height:28px;border:1px solid var(--hz-line);background:#fff;cursor:pointer;font-size:16px}" +
    ".hz-cdel{background:none;border:none;color:var(--hz-mut);cursor:pointer;font-size:12px;text-transform:uppercase;letter-spacing:.08em}.hz-cdel:hover{color:var(--hz-ink)}" +
    ".hz-cfoot{display:flex;align-items:center;justify-content:space-between;margin-top:22px}.hz-ctotal{font-size:14px;text-transform:uppercase;letter-spacing:.08em}.hz-ctotal b{font-size:22px;margin-left:8px}" +
    ".hz-done{text-align:center;padding:40px 10px}.hz-done-ico{width:64px;height:64px;border-radius:50%;background:var(--hz-ink);color:#fff;font-size:32px;display:flex;align-items:center;justify-content:center;margin:0 auto 18px}.hz-done h2{font-size:24px;margin:0 0 10px}.hz-done p{color:var(--hz-mut);line-height:1.7;margin-bottom:24px}" +
    ".hz-modal-foot{display:flex;gap:10px;padding:14px;border-top:1px solid var(--hz-line)}" +
    ".hz-modal-input{flex:1;padding:12px;border:1px solid var(--hz-line);font-size:14px;outline:none}.hz-modal-input:focus{border-color:var(--hz-ink)}" +
    ".hz-modal-send{padding:0 20px;background:var(--hz-ink);color:#fff;border:none;cursor:pointer;font-size:12px;letter-spacing:.1em;text-transform:uppercase}" +
    ".hz-bubble{padding:11px 14px;margin:7px 0;max-width:86%;white-space:pre-wrap;word-break:break-word;font-size:14px;line-height:1.6}" +
    ".hz-user{background:var(--hz-ink);color:#fff;margin-left:auto}.hz-assistant{background:var(--hz-soft);color:var(--hz-ink);margin-right:auto}" +
    ".hz-toast{position:fixed;bottom:40px;left:50%;transform:translateX(-50%) translateY(20px);background:var(--hz-ink);color:#fff;padding:12px 20px;font-size:13px;letter-spacing:.04em;z-index:100000;opacity:0;transition:.3s}.hz-toast.show{opacity:1;transform:translateX(-50%) translateY(0)}" +
    ".hz-cs-fab{position:fixed;right:24px;bottom:24px;z-index:9500;width:56px;height:56px;border-radius:50%;border:none;background:var(--hz-ink);color:#fff;font-size:24px;cursor:pointer;box-shadow:0 8px 24px rgba(0,0,0,.25)}";
  document.head.appendChild(css);

  ensureFab();
  toggleShop();
  // 监听 SPA 路由变化
  var _ps = history.pushState; history.pushState = function () { _ps.apply(this, arguments); setTimeout(toggleShop, 50); };
  window.addEventListener("popstate", function () { setTimeout(toggleShop, 50); });
  setInterval(toggleShop, 600);
})();
