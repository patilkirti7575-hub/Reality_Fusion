/**
 * story_music.js — Professional audio player for RealityFusion Story Editor
 * Handles preview playback, story audio, autoplay fallback, error recovery.
 */

(function() {
    'use strict';

    // ============================================================
    // 1. CENTRALIZED AUDIO ENGINE
    // ============================================================
    var AudioEngine = {
        _ctx: null,
        _element: null,
        _currentId: null,
        _playing: false,
        _volume: 0.7,
        _muted: false,
        _callbacks: {},

        /**
         * Get or create the shared <audio> element.
         * Using ONE element prevents multiple-audio conflicts.
         */
        getElement: function() {
            if (!this._element) {
                this._element = document.getElementById('storyAudioPlayer');
                if (!this._element) {
                    this._element = document.createElement('audio');
                    this._element.id = 'storyAudioPlayer';
                    this._element.preload = 'auto';
                    this._element.style.display = 'none';
                    document.body.appendChild(this._element);
                }
                // Wire up events once
                var self = this;
                this._element.addEventListener('play', function() { self._playing = true; self._fire('play'); });
                this._element.addEventListener('pause', function() { self._playing = false; self._fire('pause'); });
                this._element.addEventListener('ended', function() { self._playing = false; self._fire('ended'); });
                this._element.addEventListener('error', function(e) {
                    console.error('[AudioEngine] Error:', self._element.error ? self._element.error.message : 'unknown');
                    self._fire('error', self._element.error);
                });
                this._element.addEventListener('canplaythrough', function() {
                    self._fire('ready');
                });
            }
            return this._element;
        },

        /**
         * Unlock AudioContext on first user gesture (required by Chrome).
         */
        unlock: function() {
            if (this._ctx) return;
            try {
                this._ctx = new (window.AudioContext || window.webkitAudioContext)();
                if (this._ctx.state === 'suspended') {
                    this._ctx.resume().then(function() {
                        console.log('[AudioEngine] AudioContext unlocked');
                    }).catch(function(e) {
                        console.warn('[AudioEngine] AudioContext resume failed:', e);
                    });
                }
            } catch (e) {
                console.warn('[AudioEngine] AudioContext not available:', e);
            }
        },

        /**
         * Play a URL. Returns a promise that resolves when playback starts.
         */
        play: function(id, url) {
            var self = this;
            // Unlock on every play attempt (safe)
            this.unlock();

            return new Promise(function(resolve, reject) {
                if (!url) {
                    reject(new Error('No URL provided'));
                    return;
                }

                console.log('[AudioEngine] play id=' + id + ' url=' + url);

                // Stop current playback first
                self.stop();

                var el = self.getElement();
                el.src = url;
                el.volume = self._muted ? 0 : self._volume;
                el.muted = self._muted;
                el.load();

                var playPromise = el.play();
                if (playPromise && typeof playPromise.then === 'function') {
                    playPromise.then(function() {
                        console.log('[AudioEngine] playback started id=' + id);
                        self._currentId = id;
                        self._playing = true;
                        resolve();
                    }).catch(function(err) {
                        console.warn('[AudioEngine] play rejected:', err.message || err);
                        // Autoplay fallback: try resuming AudioContext + retry
                        if (self._ctx && self._ctx.state === 'suspended') {
                            self._ctx.resume().then(function() {
                                console.log('[AudioEngine] retrying after context resume');
                                var retryPromise = el.play();
                                if (retryPromise && typeof retryPromise.then === 'function') {
                                    retryPromise.then(function() {
                                        self._currentId = id;
                                        self._playing = true;
                                        resolve();
                                    }).catch(function(e2) {
                                        reject(e2);
                                    });
                                } else {
                                    reject(err);
                                }
                            }).catch(function() {
                                reject(err);
                            });
                        } else {
                            reject(err);
                        }
                    });
                } else {
                    // Older browsers: no promise support
                    self._currentId = id;
                    self._playing = true;
                    resolve();
                }
            });
        },

        /**
         * Stop playback and reset.
         */
        stop: function() {
            if (this._element) {
                this._element.pause();
                this._element.removeAttribute('src');
                this._element.load(); // Reset media resource
            }
            this._currentId = null;
            this._playing = false;
        },

        /**
         * Pause without resetting source.
         */
        pause: function() {
            if (this._element) {
                this._element.pause();
            }
            this._playing = false;
        },

        /**
         * Resume playback.
         */
        resume: function() {
            if (this._element && this._element.src) {
                var self = this;
                var p = this._element.play();
                if (p && typeof p.then === 'function') {
                    p.catch(function(err) {
                        console.warn('[AudioEngine] resume failed:', err);
                    });
                }
            }
        },

        /**
         * Set volume (0.0 - 1.0).
         */
        setVolume: function(v) {
            this._volume = Math.max(0, Math.min(1, v));
            if (this._element) {
                this._element.volume = this._volume;
            }
        },

        /**
         * Toggle mute.
         */
        toggleMute: function() {
            this._muted = !this._muted;
            if (this._element) {
                this._element.muted = this._muted;
            }
            return this._muted;
        },

        /**
         * Get current playback info.
         */
        getStatus: function() {
            var el = this._element;
            return {
                id: this._currentId,
                playing: this._playing,
                paused: el ? el.paused : true,
                currentTime: el ? el.currentTime : 0,
                duration: el ? (el.duration || 0) : 0,
                volume: this._volume,
                muted: this._muted,
                src: el ? el.src : null
            };
        },

        /**
         * Register callback for event.
         */
        on: function(event, fn) {
            if (!this._callbacks[event]) this._callbacks[event] = [];
            this._callbacks[event].push(fn);
        },

        /**
         * Remove callback.
         */
        off: function(event, fn) {
            if (!this._callbacks[event]) return;
            this._callbacks[event] = this._callbacks[event].filter(function(f) { return f !== fn; });
        },

        _fire: function(event, data) {
            if (!this._callbacks[event]) return;
            this._callbacks[event].forEach(function(fn) { fn(data); });
        }
    };

    // ============================================================
    // 2. UI INTEGRATION — Story Editor
    // ============================================================

    var currentPreviewId = null;
    var previewCards = {}; // id -> card element

    /**
     * Toggle preview of a music track (called from onclick).
     */
    window.togglePreview = function(id, url) {
        console.log('[Music] togglePreview id=' + id);

        // If clicking the same track that's playing, stop it
        if (AudioEngine._currentId === id && AudioEngine._playing) {
            AudioEngine.stop();
            updateCardPlaying(null);
            return;
        }

        // Play the track
        AudioEngine.play(id, url).then(function() {
            console.log('[Music] now playing id=' + id);
            updateCardPlaying(id);
        }).catch(function(err) {
            console.warn('[Music] playback failed:', err.message || err);
            updateCardPlaying(null);
            // Show hint on card
            var card = document.querySelector('.music-card[data-id="' + id + '"]');
            if (card) {
                card.classList.add('play-failed');
                setTimeout(function() { card.classList.remove('play-failed'); }, 2000);
            }
        });
    };

    /**
     * Update visual state of music cards.
     */
    function updateCardPlaying(id) {
        document.querySelectorAll('.music-card.playing').forEach(function(c) { c.classList.remove('playing'); });
        if (id) {
            var card = document.querySelector('.music-card[data-id="' + id + '"]');
            if (card) card.classList.add('playing');
        }
        // Update play button icons
        document.querySelectorAll('.music-play-btn i').forEach(function(icon) {
            var card = icon.closest('.music-card');
            if (card && id && card.getAttribute('data-id') === id) {
                icon.className = 'bi bi-pause-fill';
            } else {
                icon.className = 'bi bi-play-fill';
            }
        });
    }

    /**
     * Select a music track for the story (called when clicking card text area).
     */
    window.selectMusic = function(id) {
        console.log('[Music] select id=' + id);
        // Stop any playing preview
        AudioEngine.stop();
        updateCardPlaying(null);

        selectedAudioId = id;
        document.querySelectorAll('.music-card').forEach(function(c) { c.classList.remove('selected'); });

        if (id) {
            var card = document.querySelector('.music-card[data-id="' + id + '"]');
            if (card) {
                card.classList.add('selected');
                var indicator = document.getElementById('musicIndicator');
                if (indicator) {
                    indicator.style.display = 'block';
                    var label = document.getElementById('musicLabel');
                    if (label) {
                        var title = (card.querySelector('.m-title') || {}).textContent || '';
                        var artist = (card.querySelector('.m-artist') || {}).textContent || '';
                        label.textContent = title + ' - ' + artist;
                    }
                }
            }
        } else {
            var noMusic = document.getElementById('noMusicCard');
            if (noMusic) noMusic.classList.add('selected');
            var indicator = document.getElementById('musicIndicator');
            if (indicator) indicator.style.display = 'none';
        }
    };

    /**
     * Search and filter music (called from search input).
     */
    window.searchMusic = function(query) {
        var q = (query || '').toLowerCase().trim();
        document.querySelectorAll('.music-card[data-id]').forEach(function(c) {
            var title = (c.querySelector('.m-title') || {}).textContent || '';
            var artist = (c.querySelector('.m-artist') || {}).textContent || '';
            var lang = c.getAttribute('data-lang') || '';
            var matchesSearch = !q || title.toLowerCase().includes(q) || artist.toLowerCase().includes(q) || lang.includes(q);
            var langFilter = window.musicLangFilter || 'all';
            var matchesLang = langFilter === 'all' || lang === langFilter;
            c.style.display = (matchesSearch && matchesLang) ? '' : 'none';
        });
        // API search for more results
        if (q.length >= 2) {
            var langParam = window.musicLangFilter || 'all';
            fetch('/api/story/music/search/?q=' + encodeURIComponent(q) + '&lang=' + langParam)
                .then(function(r) { return r.json(); })
                .then(function(data) {
                    if (data.music && data.music.length > 0) {
                        renderMusicResults(data.music);
                    }
                })
                .catch(function() {});
        }
    };

    /**
     * Filter by language (called from lang filter buttons).
     */
    window.filterMusicByLang = function(lang, btn) {
        window.musicLangFilter = lang;
        document.querySelectorAll('.lang-filter').forEach(function(b) {
            b.style.background = 'transparent';
            b.style.color = '#aaa';
            b.style.borderColor = '#363636';
        });
        if (btn) {
            btn.style.background = 'rgba(0,149,246,0.15)';
            btn.style.color = '#0095f6';
            btn.style.borderColor = '#0095f6';
        }
        var searchInput = document.getElementById('musicSearch');
        window.searchMusic(searchInput ? searchInput.value : '');
    };

    /**
     * Render API search results.
     */
    function renderMusicResults(tracks) {
        document.querySelectorAll('.music-card.api-result').forEach(function(c) { c.remove(); });
        var list = document.getElementById('musicList');
        if (!list) return;
        tracks.forEach(function(t) {
            if (document.querySelector('.music-card[data-id="' + t.id + '"]')) return;
            var card = document.createElement('div');
            card.className = 'music-card api-result';
            card.setAttribute('data-id', t.id);
            card.setAttribute('data-lang', (t.language || '').toLowerCase());
            card.setAttribute('data-audio', t.audio_url || '');

            var coverHtml = t.cover_url
                ? '<img src="' + t.cover_url + '">'
                : '<div class="music-cover-placeholder"><i class="bi bi-music-note"></i></div>';

            card.innerHTML =
                '<div class="music-cover-wrap" onclick="event.stopPropagation();togglePreview(\'' + t.id + '\',\'' + (t.audio_url || '') + '\')">'
                + coverHtml
                + '<div class="music-play-btn"><i class="bi bi-play-fill"></i></div></div>'
                + '<div class="music-meta" onclick="selectMusic(' + t.id + ')">'
                + '<div class="m-title">' + (t.title || 'Unknown') + '</div>'
                + '<div class="m-artist">' + (t.artist || '') + '</div>'
                + (t.language ? '<div class="m-lang">' + t.language + '</div>' : '')
                + '</div>';

            list.appendChild(card);
        });
    }

    // ============================================================
    // 3. AUTOPLAY FALLBACK — After any user click, unlock audio
    // ============================================================

    function globalUnlock() {
        AudioEngine.unlock();
    }
    document.addEventListener('click', globalUnlock, { once: true });
    document.addEventListener('touchstart', globalUnlock, { once: true });
    document.addEventListener('keydown', globalUnlock, { once: true });

    // ============================================================
    // 4. STORY VIEWER — Attached music playback
    // ============================================================

    /**
     * Play story music when story viewer loads.
     * Call from story_view.html on page load.
     */
    window.playStoryMusic = function(url) {
        if (!url) return;
        console.log('[StoryMusic] starting story audio:', url);
        AudioEngine.unlock();
        AudioEngine.play('story', url).then(function() {
            console.log('[StoryMusic] story audio playing');
        }).catch(function(err) {
            console.warn('[StoryMusic] story audio failed:', err);
            // Story music failure is non-critical
        });
    };

    /**
     * Toggle story music play/pause.
     */
    window.toggleStoryMusic = function() {
        var status = AudioEngine.getStatus();
        if (status.src) {
            if (status.playing) {
                AudioEngine.pause();
            } else {
                AudioEngine.resume();
            }
        }
    };

    /**
     * Toggle story music mute.
     */
    window.toggleStoryMute = function() {
        var muted = AudioEngine.toggleMute();
        var btn = document.querySelector('.story-music-btn i');
        if (btn) {
            btn.className = muted ? 'bi bi-volume-mute-fill' : 'bi bi-volume-up-fill';
        }
        return muted;
    };

    // ============================================================
    // 5. INIT — Activate "All" language filter, expose engine
    // ============================================================

    (function init() {
        // Activate "All" language filter on page load
        var allBtn = document.querySelector('.lang-filter[data-lang="all"]');
        if (allBtn) {
            allBtn.style.background = 'rgba(0,149,246,0.15)';
            allBtn.style.color = '#0095f6';
            allBtn.style.borderColor = '#0095f6';
        }
        console.log('[Music] AudioEngine initialized');
    })();

    // Expose AudioEngine for debug
    window.AudioEngine = AudioEngine;

})();
