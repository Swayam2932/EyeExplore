/**
 * k_sync.js
 * ---------------------------------------------------------------------------
 * Synchronises the HTML5 video player (#k-video-player) with the Plotly
 * K-Coefficient Timeline chart (#right-graph) in the EyeExplore Dash app.
 */
(function () {
  'use strict';

  var fixations = [];
  var trailHistory = [];
  var TRAIL_LENGTH = 5;
  var MAIN_DOT_SIZE = 16;
  var CLS_PREFIX = 'ksync';
  var looping = false;
  var lastTime = -1;
  var lastPlotlyUpdate = 0;

  function injectStyles() {
    if (document.getElementById(CLS_PREFIX + '-styles')) return;
    var style = document.createElement('style');
    style.id = CLS_PREFIX + '-styles';
    style.textContent = `
      .${CLS_PREFIX}-dot {
        position: absolute;
        border-radius: 50%;
        transform: translate(-50%, -50%);
        pointer-events: none;
        z-index: 1000;
        transition: left 0.1s linear, top 0.1s linear, background-color 0.1s linear;
      }
      .${CLS_PREFIX}-dot-main {
        width: ${MAIN_DOT_SIZE}px;
        height: ${MAIN_DOT_SIZE}px;
        z-index: 1001;
      }
      .${CLS_PREFIX}-dot-trail {
        width: 8px;
        height: 8px;
        border: 1px solid white;
        background-color: white;
      }
    `;
    document.head.appendChild(style);
  }

  function loadFixationData() {
    var dataDiv = document.getElementById('k-fixation-data');
    if (dataDiv && dataDiv.textContent) {
      try {
        var rawData = JSON.parse(dataDiv.textContent);
        if (Array.isArray(rawData)) {
          rawData.sort(function (a, b) { return a.time_sec - b.time_sec; });
          fixations = rawData;
        } else {
          fixations = [];
        }
      } catch (e) {
        fixations = [];
      }
    } else {
      fixations = [];
    }
  }

  function findClosestFixation(target) {
    if (fixations.length === 0) return null;

    var lo = 0;
    var hi = fixations.length - 1;

    while (lo < hi) {
      var mid = (lo + hi) >>> 1;
      if (fixations[mid].time_sec < target) {
        lo = mid + 1;
      } else {
        hi = mid;
      }
    }

    if (lo > 0) {
      var diffLo = Math.abs(fixations[lo].time_sec - target);
      var diffPrev = Math.abs(fixations[lo - 1].time_sec - target);
      if (diffPrev < diffLo) {
        return fixations[lo - 1];
      }
    }

    return fixations[lo];
  }

  function ensureTrailDots(container) {
    var existing = container.querySelectorAll('.' + CLS_PREFIX + '-dot-trail');
    if (existing.length < TRAIL_LENGTH) {
      for (var i = existing.length; i < TRAIL_LENGTH; i++) {
        var dot = document.createElement('div');
        dot.className = CLS_PREFIX + '-dot ' + CLS_PREFIX + '-dot-trail';
        dot.style.display = 'none';
        container.appendChild(dot);
      }
    }
  }

  function updateTrail(xPct, yPct, color, container) {
    ensureTrailDots(container);

    trailHistory.push({ x: xPct, y: yPct, color: color });

    if (trailHistory.length > TRAIL_LENGTH) {
      trailHistory = trailHistory.slice(trailHistory.length - TRAIL_LENGTH);
    }

    var trailNodes = container.querySelectorAll('.' + CLS_PREFIX + '-dot-trail');
    var age = 0;
    for (var i = trailHistory.length - 1; i >= 0; i--) {
      var entry = trailHistory[i];
      var dot = trailNodes[age];
      if (!dot) break;

      var opacity = 0.15 + 0.55 * (age / (TRAIL_LENGTH - 1 || 1));

      dot.style.display = 'block';
      dot.style.left = entry.x + 'px';
      dot.style.top = entry.y + 'px';
      dot.style.backgroundColor = entry.color;
      dot.style.opacity = opacity;

      age++;
    }

    for (var j = age; j < trailNodes.length; j++) {
      trailNodes[j].style.display = 'none';
    }
  }

  function sync() {
    var video = document.getElementById('k-video-player');
    if (!video) return;

    var currentTime = video.currentTime;
    
    if (currentTime === lastTime && video.paused) return;
    lastTime = currentTime;

    var container = document.getElementById('k-video-container');
    var mainDot = document.getElementById('k-fixation-dot');
    var fix = findClosestFixation(currentTime);

    if (fix && container && mainDot) {
      var color = 'black';

      var videoRatio = video.videoWidth / video.videoHeight;
      var containerW = video.clientWidth;
      var containerH = video.clientHeight;
      var containerRatio = containerW / containerH;

      var renderW = containerW, renderH = containerH, offsetX = 0, offsetY = 0;
      
      if (videoRatio && containerRatio) {
        if (containerRatio > videoRatio) {
          renderH = containerH;
          renderW = renderH * videoRatio;
          offsetX = (containerW - renderW) / 2;
        } else {
          renderW = containerW;
          renderH = renderW / videoRatio;
          offsetY = (containerH - renderH) / 2;
        }
      }

      var finalX = offsetX + (fix.x_pct / 100) * renderW;
      var finalY = offsetY + (fix.y_pct / 100) * renderH;

      mainDot.style.left = finalX + 'px';
      mainDot.style.top = finalY + 'px';
      mainDot.style.backgroundColor = color;
      mainDot.style.border = '2px solid white';
      mainDot.style.display = 'block';

      if (!mainDot.classList.contains(CLS_PREFIX + '-dot')) {
        mainDot.classList.add(CLS_PREFIX + '-dot', CLS_PREFIX + '-dot-main');
      }

      updateTrail(finalX, finalY, color, container);
    } else if (mainDot) {
      mainDot.style.display = 'none';
    }

    var now = Date.now();
    if (now - lastPlotlyUpdate > 100) {
      var rightGraphWrap = document.getElementById('right-graph');
      if (rightGraphWrap && typeof Plotly !== 'undefined') {
        var plotlyDiv = rightGraphWrap.querySelector('.js-plotly-plot') || rightGraphWrap;
        try {
          var layout = plotlyDiv.layout || (plotlyDiv._fullLayout ? plotlyDiv._fullLayout : null);
          if (layout && layout.shapes && layout.shapes.length > 0) {
            var shapeIdx = 0;
            for (var i = 0; i < layout.shapes.length; i++) {
              if (layout.shapes[i].name === 'scrubber' || (layout.shapes[i].line && layout.shapes[i].line.color === 'red')) {
                shapeIdx = i;
                break;
              }
            }
            var update = {};
            update['shapes[' + shapeIdx + '].x0'] = currentTime;
            update['shapes[' + shapeIdx + '].x1'] = currentTime;
            Plotly.relayout(plotlyDiv, update);
            lastPlotlyUpdate = now;
          }
        } catch (err) {
          console.error("k_sync.js Plotly error:", err);
        }
      }
    }
  }

  function startGlobalLoop() {
    if (looping) return;
    looping = true;
    (function loop() {
      sync();
      requestAnimationFrame(loop);
    })();
  }

  function init() {
    injectStyles();
    
    setInterval(function() {
      var dataDiv = document.getElementById('k-fixation-data');
      if (dataDiv && !dataDiv.dataset.observed) {
        dataDiv.dataset.observed = 'true';
        var observer = new MutationObserver(function () {
          loadFixationData();
        });
        observer.observe(dataDiv, { childList: true, characterData: true, subtree: true });
        loadFixationData();
      }
    }, 1000);
    
    startGlobalLoop();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
