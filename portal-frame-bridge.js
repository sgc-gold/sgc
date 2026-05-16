(function () {
  if (window.top === window.self || !window.parent) return;

  var tracking = false;
  var armed = false;
  var pulling = false;
  var refreshing = false;
  var startY = 0;
  var startX = 0;
  var maxPull = 96;
  var triggerPull = 72;
  var startBand = 120;
  var scrollTicking = false;
  var lastAtTop = null;

  function getScrollTop() {
    return Math.max(
      window.pageYOffset || 0,
      document.documentElement ? document.documentElement.scrollTop : 0,
      document.body ? document.body.scrollTop : 0
    );
  }

  function atTop() {
    return getScrollTop() <= 2;
  }

  function postMessage(type, extra) {
    var payload = { type: type };
    if (extra) {
      for (var key in extra) payload[key] = extra[key];
    }
    window.parent.postMessage(payload, '*');
  }

  function postScrollState(force) {
    var nextAtTop = atTop();
    if (!force && nextAtTop === lastAtTop) return;
    lastAtTop = nextAtTop;
    postMessage('scroll-state', { atTop: nextAtTop });
  }

  function resetPullState() {
    tracking = false;
    armed = false;
    pulling = false;
    postMessage('pull-refresh-reset');
  }

  function finishRefresh() {
    refreshing = false;
    postScrollState(true);
    postMessage('pull-refresh-done');
  }

  function runRefresh() {
    if (refreshing) return;
    refreshing = true;
    try {
      if (typeof window.portalRefresh === 'function') {
        Promise.resolve(window.portalRefresh()).then(finishRefresh, function () {
          finishRefresh();
        });
      } else {
        window.location.reload();
      }
    } catch (err) {
      finishRefresh();
    }
  }

  window.addEventListener('scroll', function () {
    if (scrollTicking) return;
    scrollTicking = true;
    window.requestAnimationFrame(function () {
      scrollTicking = false;
      postScrollState(false);
    });
  }, { passive: true });

  window.addEventListener('load', function () {
    postScrollState(true);
  });

  window.addEventListener('resize', function () {
    postScrollState(true);
  });

  window.addEventListener('touchstart', function (event) {
    if (refreshing) return;
    if (!event.touches || event.touches.length !== 1) return;
    if (!atTop()) return;
    if (event.touches[0].clientY > startBand) return;
    tracking = true;
    armed = false;
    pulling = false;
    startX = event.touches[0].clientX;
    startY = event.touches[0].clientY;
    postMessage('pull-refresh-progress', { progress: 0, armed: false });
  }, { passive: true });

  window.addEventListener('touchmove', function (event) {
    if (refreshing || !tracking || !event.touches || event.touches.length !== 1) return;
    var deltaX = event.touches[0].clientX - startX;
    var deltaY = event.touches[0].clientY - startY;
    if (deltaY <= 0) return;
    if (Math.abs(deltaX) > Math.max(12, deltaY * 0.75)) {
      resetPullState();
      return;
    }
    if (!pulling && deltaY < 8) return;
    pulling = true;

    event.preventDefault();
    var clamped = Math.min(deltaY, maxPull);
    armed = clamped >= triggerPull;
    postMessage('pull-refresh-progress', {
      progress: clamped / maxPull,
      armed: armed
    });
  }, { passive: false });

  window.addEventListener('touchend', function () {
    if (!tracking) return;
    if (armed) postMessage('refresh-current-frame');
    else postMessage('pull-refresh-reset');
    tracking = false;
    armed = false;
    pulling = false;
  }, { passive: true });

  window.addEventListener('touchcancel', resetPullState, { passive: true });

  window.addEventListener('message', function (event) {
    if (!event.data || event.data.type !== 'portal-refresh') return;
    runRefresh();
  });
})();
