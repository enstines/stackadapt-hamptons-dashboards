/* Minimal stand-in for the Claude Dashboard runtime so the same page can run on any static host.
   Provides: dash.data(id), dash.onData(cb), dash.calc(name, {inputs, fn}), dash.params(), dash.setParams(p), dash.colors */
(function () {
  var base = (document.currentScript && document.currentScript.dataset.base) || './data/';
  var sets = {};        // id -> {status, data}
  var calcs = {};       // id -> {inputs, fn}
  var listeners = [];
  var params = {};
  var scheduled = false;

  function get(id) { return sets[id] || (sets[id] = { status: 'loading', data: undefined }); }
  function fire() {
    if (scheduled) return; scheduled = true;
    requestAnimationFrame(function () { scheduled = false; listeners.forEach(function (cb) { try { cb(); } catch (e) { setTimeout(function () { throw e; }); } }); });
  }
  function runCalcs() {
    Object.keys(calcs).forEach(function (id) {
      var c = calcs[id], s = get(id);
      if (s.status === 'ok') return;
      var ins = c.inputs.map(get);
      if (ins.some(function (x) { return x.status === 'error'; })) { s.status = 'error'; return; }
      if (ins.every(function (x) { return x.status === 'ok'; })) {
        try { s.data = c.fn.apply(null, ins.map(function (x) { return x.data; })); s.status = 'ok'; } catch (e) { s.status = 'error'; console.error(id, e); }
      }
    });
  }
  function readHash() {
    var out = {};
    new URLSearchParams(location.hash.replace(/^#/, '')).forEach(function (v, k) { out[k] = v; });
    return out;
  }
  params = Object.assign({}, window.DASH_INITIAL_PARAMS || {}, readHash());

  window.dash = {
    colors: ['#081631', '#a29992', '#2e9e83', '#2892b9', '#d98e04', '#8e5ea2', '#c0504d', '#4f81bd', '#7f7f7f', '#3b7a57'],
    data: function (id) { var s = get(id); return { status: s.status, data: s.data }; },
    onData: function (cb) { listeners.push(cb); fire(); },
    calc: function (id, spec) { calcs[id] = spec; get(id); runCalcs(); },
    params: function () { return params; },
    setParams: function (p) {
      params = Object.assign({}, params, p);
      Object.keys(params).forEach(function (k) { if (params[k] === null || params[k] === undefined || params[k] === '') delete params[k]; });
      var h = new URLSearchParams(params).toString();
      try { history.replaceState(null, '', location.pathname + location.search + (h ? '#' + h : '')); } catch (e) {}
      fire();
    },
  };

  window.addEventListener('hashchange', function () { params = Object.assign({}, window.DASH_INITIAL_PARAMS || {}, readHash()); fire(); });

  (window.DASH_DATASETS || []).forEach(function (id) {
    var s = get(id);
    fetch(base + id + '.json', { cache: 'no-cache' })
      .then(function (r) { if (!r.ok) throw new Error(r.status); return r.json(); })
      .then(function (rows) { s.data = rows; s.status = 'ok'; })
      .catch(function (e) { console.error('dataset', id, e); s.status = 'error'; })
      .then(function () { runCalcs(); fire(); });
  });
})();
