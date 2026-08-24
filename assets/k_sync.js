/**
 * k_sync.js
 * ---------------------------------------------------------------------------
 * Synchronises the HTML5 video player (#k-video-player) with the Plotly
 * K-Coefficient Timeline chart (#right-graph) in the EyeExplore Dash app.
 *
 * Features
 *  - Binary-search lookup of the closest fixation point for the current time
 *  - Fixation dot overlay positioned as % of the video container
 *  - Diverging colour scheme (blue = focal / red = ambient) driven by k_squashed
 *  - Trail of the last 5 fixation positions with fade-out
 *  - Vertical scrubber line updated on the Plotly chart via Plotly.relayout
 *  - requestAnimationFrame loop while the video is playing
 *  - MutationObserver on #k-fixation-data to pick up Dash-driven updates
 * ---------------------------------------------------------------------------
 */
(function () {
  'use strict';

  /* ======================================================================
   * CONSTANTS
   * ==================================================================== */

  /** Number of trail dots to keep (excluding the main dot). */
  var TRAIL_LENGTH = 5;

  /** Diameter of the main fixation dot in pixels. */
  var MAIN_DOT_SIZE = 16;

  /** Diameter of each trail dot in pixels. */
  var TRAIL_DOT_SIZE = 8;

  /** CSS class prefix used for all injected elements. */
  var CLS_PREFIX = 'ksync';

  /* ======================================================================
   * STATE
   * ==================================================================== */

  /** Parsed fixation data array — kept sorted by time_sec. */
  var fixations = [];

  /** Ring-buffer of the last TRAIL_LENGTH positions for the trail effect. */
  var trailHistory = [];

  /** Reference to the requestAnimationFrame id so we can cancel it. */
  var rafId = null;

  /** Whether the rAF loop is currently active. */
  var looping = false;

  /* ======================================================================
   * HELPERS
   * ==================================================================== */

  /**
   * Binary-search `fixations` for the entry whose `time_sec` is closest to
   * `target`.  Returns the fixation object, or null when the array is empty.
   *
   * @param {number} target - The video currentTime in seconds.
   * @returns {Object|null}
   */
  function findClosestFixation(target) {
    if (fixations.length === 0) return null;

    var lo = 0;
    var hi = fixations.length - 1;

    // Standard binary search — narrow to 2-element window.
    while (lo < hi) {
      var mid = (lo + hi) >>> 1;
      if (fixations[mid].time_sec < target) {
        lo = mid + 1;
      } else {
        hi = mid;
      }
    }

    // lo === hi — compare with the predecessor if it exists.
    if (lo > 0) {
      var diffLo = Math.abs(fixations[lo].time_sec - target);
      var diffPrev = Math.abs(fixations[lo - 1].time_sec - target);
      if (diffPrev < diffLo) {
        return fixations[lo - 1];
      }
    }

    return fixations[lo];
  }

  /**
   * Map a k_squashed value in [-1, 1] to an rgba colour string.
   *
   * Positive (focal)  → blue   (rgb  70, 130, 230)
   * Negative (ambient) → red    (rgb 220,  60,  60)
   * Zero               → neutral grey
   *
   * Intensity (alpha) is proportional to |k_squashed|, clamped to [0.25, 1].
   *
   * @param {number} k - The squashed K-coefficient, expected ∈ [-1, 1].
   * @returns {string} CSS rgba colour.
   */
  function kToColor(k) {
    var magnitude = Math.min(Math.abs(k), 1);
    var alpha = 0.25 + 0.75 * magnitude; // keep a minimum visibility

    if (k >= 0) {
      // Focal — blue, intensity increases with k
      var r = Math.round(70 + (200 - 70) * (1 - magnitude));   // fade toward grey
      var g = Math.round(130 + (200 - 130) * (1 - magnitude));
      var b = Math.round(230 + (200 - 230) * (1 - magnitude));
      return 'rgba(' + r + ',' + g + ',' + b + ',' + alpha + ')';
    } else {
      // Ambient — red, intensity increases with |k|
      var r2 = Math.round(220 + (200 - 220) * (1 - magnitude));
      var g2 = Math.round(60  + (200 - 60)  * (1 - magnitude));
      var b2 = Math.round(60  + (200 - 60)  * (1 - magnitude));
      return 'rgba(' + r2 + ',' + g2 + ',' + b2 + ',' + alpha + ')';
    }
  }

  /* ======================================================================
   * DOM — INJECT STYLES ONCE
   * ==================================================================== */

  /**
   * Inject a minimal <style> block for the fixation dots.  Called once.
   */
  function injectStyles() {
    if (document.getElementById(CLS_PREFIX + '-style')) return;

    var css = [
      '.' + CLS_PREFIX + '-dot {',
      '  position: absolute;',
      '  border-radius: 50%;',
      '  pointer-events: none;',
      '  transform: translate(-50%, -50%);',
      '  box-sizing: border-box;',
      '  border: 2px solid rgba(255,255,255,0.9);',
      '  transition: left 0.04s linear, top 0.04s linear;',
      '  z-index: 10;',
      '}',
      '.' + CLS_PREFIX + '-dot-main {',
      '  width: ' + MAIN_DOT_SIZE + 'px;',
      '  height: ' + MAIN_DOT_SIZE + 'px;',
      '  z-index: 11;',
      '}',
      '.' + CLS_PREFIX + '-dot-trail {',
      '  width: ' + TRAIL_DOT_SIZE + 'px;',
      '  height: ' + TRAIL_DOT_SIZE + 'px;',
      '  border-width: 1px;',
      '}'
    ].join('\n');

    var style = document.createElement('style');
    style.id = CLS_PREFIX + '-style';
    style.textContent = css;
    document.head.appendChild(style);
  }

  /* ======================================================================
   * DOM — TRAIL DOT MANAGEMENT
   * ==================================================================== */

  /** Array of trail-dot DOM elements (oldest first). */
  var trailDots = [];

  /**
   * Ensure that exactly TRAIL_LENGTH trail-dot elements exist inside the
   * given container.
   *
   * @param {HTMLElement} container - #k-video-container
   */
  function ensureTrailDots(container) {
    // Remove stale ones that may have been orphaned by Dash re-renders.
    trailDots = trailDots.filter(function (el) {
      return el.parentNode === container;
    });

    while (trailDots.length < TRAIL_LENGTH) {
      var dot = document.createElement('div');
      dot.className = CLS_PREFIX + '-dot ' + CLS_PREFIX + '-dot-trail';
      dot.style.display = 'none';
      container.appendChild(dot);
      trailDots.push(dot);
    }
  }

  /**
   * Push the current fixation position into the trail ring-buffer and
   * update the trail-dot DOM elements.
   *
   * @param {number} xPct - x position (0-100).
   * @param {number} yPct - y position (0-100).
   * @param {string} color - CSS colour for the dot.
   * @param {HTMLElement} container - #k-video-container.
   */
  function updateTrail(xPct, yPct, color, container) {
    ensureTrailDots(container);

    // Push new position.
    trailHistory.push({ x: xPct, y: yPct, color: color });

    // Keep only the last TRAIL_LENGTH entries.
    if (trailHistory.length > TRAIL_LENGTH) {
      trailHistory = trailHistory.slice(trailHistory.length - TRAIL_LENGTH);
    }

    // Update DOM.
    for (var i = 0; i < TRAIL_LENGTH; i++) {
      var dot = trailDots[i];
      var entry = trailHistory[trailHistory.length - TRAIL_LENGTH + i]; // may be undefined

      if (!entry) {
        dot.style.display = 'none';
        continue;
      }

      // Oldest trail point = index 0 → most faded.
      // `age` runs from 0 (oldest visible) to TRAIL_LENGTH-1 (newest visible).
      var age = i - (TRAIL_LENGTH - trailHistory.length);
      if (age < 0) {
        dot.style.display = 'none';
        continue;
      }

      var opacity = 0.15 + 0.55 * (age / (TRAIL_LENGTH - 1 || 1));

      dot.style.display = 'block';
      dot.style.left = entry.x + 'px';
      dot.style.top = entry.y + 'px';
      dot.style.backgroundColor = entry.color;
      dot.style.opacity = opacity;
    }
  }

  /* ======================================================================
   * CORE SYNC LOGIC
   * ==================================================================== */

  /**
   * Called on every sync tick (timeupdate or rAF).
   * Reads the video's currentTime, updates the fixation dot + trail,
   * and moves the Plotly scrubber line.
   *
   * @param {HTMLVideoElement} video
   */
  function sync(video) {
    var currentTime = video.currentTime;

    // --- Fixation dot -------------------------------------------------------
    var container = document.getElementById('k-video-container');
    var mainDot = document.getElementById('k-fixation-dot');
    var fix = findClosestFixation(currentTime);

    if (fix && container && mainDot) {
      var color = 'black';

      // Calculate the actual rendered video dimensions due to object-fit: contain
      var videoRatio = video.videoWidth / video.videoHeight;
      var containerW = video.clientWidth;
      var containerH = video.clientHeight;
      var containerRatio = containerW / containerH;

      var renderW = containerW, renderH = containerH, offsetX = 0, offsetY = 0;
      
      if (videoRatio && containerRatio) { // Ensure metadata is loaded
        if (containerRatio > videoRatio) {
          // Pillarbox (black bars on left/right)
          renderH = containerH;
          renderW = renderH * videoRatio;
          offsetX = (containerW - renderW) / 2;
        } else {
          // Letterbox (black bars on top/bottom)
          renderW = containerW;
          renderH = renderW / videoRatio;
          offsetY = (containerH - renderH) / 2;
        }
      }

      // Convert percentages to actual pixel coordinates on the rendered video frame
      var finalX = offsetX + (fix.x_pct / 100) * renderW;
      var finalY = offsetY + (fix.y_pct / 100) * renderH;

      // Position and colour the main dot.
      mainDot.style.left = finalX + 'px';
      mainDot.style.top = finalY + 'px';
      mainDot.style.backgroundColor = color;
      mainDot.style.display = 'block';

      // Ensure the main dot carries our style classes.
      if (!mainDot.classList.contains(CLS_PREFIX + '-dot')) {
        mainDot.classList.add(CLS_PREFIX + '-dot', CLS_PREFIX + '-dot-main');
      }

      // Trail.
      updateTrail(finalX, finalY, color, container);
    }

    // --- Plotly scrubber line ------------------------------------------------
    var rightGraphWrap = document.getElementById('right-graph');
    if (rightGraphWrap && typeof Plotly !== 'undefined') {
      // Dash Plotly instances are within .js-plotly-plot
      var plotlyDiv = rightGraphWrap.querySelector('.js-plotly-plot') || rightGraphWrap;
      // Guard: only relayout if the graph has been initialised with shapes.
      try {
        var layout = plotlyDiv.layout || (plotlyDiv._fullLayout ? plotlyDiv._fullLayout : null);
        if (layout && layout.shapes && layout.shapes.length > 0) {
          Plotly.relayout(plotlyDiv, {
            'shapes[0].x0': currentTime,
            'shapes[0].x1': currentTime
          });
        }
      } catch (_ignored) {
        // Plotly may not be ready yet — silently skip.
      }
    }
  }

  /* ======================================================================
   * rAF LOOP — smooth updates while playing
   * ==================================================================== */

  /**
   * Start a requestAnimationFrame loop that calls `sync` every frame.
   *
   * @param {HTMLVideoElement} video
   */
  function startLoop(video) {
    if (looping) return;
    looping = true;

    function tick() {
      if (!looping) return;
      sync(video);
      rafId = requestAnimationFrame(tick);
    }

    rafId = requestAnimationFrame(tick);
  }

  /** Stop the rAF loop. */
  function stopLoop() {
    looping = false;
    if (rafId !== null) {
      cancelAnimationFrame(rafId);
      rafId = null;
    }
  }

  /* ======================================================================
   * FIXATION DATA PARSING
   * ==================================================================== */

  /**
   * Try to parse fixation data from the hidden div #k-fixation-data.
   * Dash writes data as the div's `textContent` (children).
   * Returns true if data was successfully loaded.
   *
   * @returns {boolean}
   */
  function loadFixationData() {
    var dataDiv = document.getElementById('k-fixation-data');
    if (!dataDiv) return false;

    var raw = (dataDiv.textContent || '').trim();
    if (!raw) return false;

    try {
      var parsed = JSON.parse(raw);
      if (Array.isArray(parsed) && parsed.length > 0) {
        // Ensure sorted by time_sec for binary search.
        parsed.sort(function (a, b) { return a.time_sec - b.time_sec; });
        fixations = parsed;
        // Reset trail when data changes.
        trailHistory = [];
        return true;
      }
    } catch (e) {
      // Bad JSON — leave fixations unchanged.
    }

    return false;
  }

  /* ======================================================================
   * BOOTSTRAP — wire everything up once DOM is ready
   * ==================================================================== */

  /**
   * Main initialisation.  Searches for the required elements, attaches
   * event listeners, and starts the MutationObserver.
   */
  function init() {
    injectStyles();

    var video = document.getElementById('k-video-player');
    if (!video) {
      // The video element doesn't exist yet — Dash may not have rendered it.
      // Retry after a short delay.
      setTimeout(init, 500);
      return;
    }

    // Load fixation data on start-up (may already be populated).
    loadFixationData();

    // --- Video events -------------------------------------------------------

    // `timeupdate` fires ~4 times/sec — used as a fallback & for seeks.
    video.addEventListener('timeupdate', function () {
      // If the rAF loop is active it already calls sync, so skip here to
      // avoid double work.  But always sync on timeupdate when paused (the
      // loop won't be running).
      if (!looping) {
        sync(video);
      }
    });

    video.addEventListener('play', function () {
      startLoop(video);
    });

    video.addEventListener('playing', function () {
      startLoop(video);
    });

    video.addEventListener('pause', function () {
      stopLoop();
      // Run one final sync to make sure the dot and line are accurate.
      sync(video);
    });

    video.addEventListener('ended', function () {
      stopLoop();
      sync(video);
    });

    video.addEventListener('seeked', function () {
      sync(video);
    });

    // --- MutationObserver on #k-fixation-data --------------------------------
    var dataDiv = document.getElementById('k-fixation-data');
    if (dataDiv) {
      var observer = new MutationObserver(function () {
        loadFixationData();
      });
      observer.observe(dataDiv, { childList: true, characterData: true, subtree: true });
    } else {
      // If the div doesn't exist yet, poll until it appears.
      var pollId = setInterval(function () {
        var div = document.getElementById('k-fixation-data');
        if (div) {
          clearInterval(pollId);
          loadFixationData();
          var obs = new MutationObserver(function () {
            loadFixationData();
          });
          obs.observe(div, { childList: true, characterData: true, subtree: true });
        }
      }, 1000);
    }
  }

  /* ======================================================================
   * ENTRY POINT — wait for the DOM
   * ==================================================================== */

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    // DOM is already ready (Dash may load assets after initial render).
    init();
  }
})();
