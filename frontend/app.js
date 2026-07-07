// ====================================================
// TaxiChi — Full Backend Integration
// ====================================================
const API_BASE = 'http://localhost:8000/api';

const app = {
  currentUser: null,
  currentRide: null,
  selectedTransport: null,
  trackingMap: null,
  driverMarker: null,
  locationPollTimer: null,
  lostItemPollTimer: null,
  _seenLostItemIds: new Set(),

  // --------------------------------------------------
  // INIT
  // --------------------------------------------------
  init() {
    const token = localStorage.getItem('access_token');
    if (token) {
      this.enterApp();
    } else {
      this.showAuthView('login');
    }
  },

  // --------------------------------------------------
  // AUTH VIEW SWITCHING (login / signup-role / etc.)
  // --------------------------------------------------
  showAuthView(viewName) {
    document.getElementById('navbar').style.display = 'none';
    document.getElementById('app-views').style.display = 'none';
    document.querySelectorAll('.view').forEach(v => { v.classList.remove('active'); v.style.display = ''; });
    const v = document.getElementById('view-' + viewName);
    if (v) { v.classList.add('active'); }
  },

  // --------------------------------------------------
  // APP VIEW SWITCHING (home / book / track / etc.)
  // --------------------------------------------------
  showView(viewName) {
    document.getElementById('navbar').style.display = 'block';
    document.getElementById('app-views').style.display = 'block';
    document.querySelectorAll('.view').forEach(v => { v.classList.remove('active'); v.style.display = ''; });
    const v = document.getElementById('view-' + viewName);
    if (v) { v.classList.add('active'); }

    // Update active nav link
    document.querySelectorAll('.nav-links a[data-view]').forEach(a => a.classList.remove('active'));
    const navLink = document.querySelector(`.nav-links a[data-view="${viewName}"]`);
    if (navLink) navLink.classList.add('active');

    if (viewName === 'track')   this.loadActiveRide();
    if (viewName === 'history') this.loadRideHistory();
    if (viewName === 'profile') this.loadProfile();
  },

  enterApp() {
    this.currentUser = {
      id:       parseInt(localStorage.getItem('user_id')),
      username: localStorage.getItem('username'),
      role:     localStorage.getItem('role'),
    };
    this._resetBooking();
    this.showView('home');
    this._startLostItemPolling();
  },

  // --------------------------------------------------
  // API HELPER  (returns parsed JSON or null on error)
  // --------------------------------------------------
  async api(endpoint, method = 'GET', data = null, errorTarget = null) {
    const token = localStorage.getItem('access_token');
    const opts = {
      method,
      headers: { 'Content-Type': 'application/json' },
    };
    if (token) opts.headers['Authorization'] = 'Bearer ' + token;
    if (data)  opts.body = JSON.stringify(data);

    let res;
    try {
      res = await fetch(API_BASE + endpoint, opts);
    } catch (e) {
      this.showError(errorTarget, 'Network error — make sure the server is running.');
      return null;
    }

    if (res.status === 401) { this.handleLogout(); return null; }
    if (res.status === 204) return {};

    const json = await res.json();
    if (!res.ok) {
      const msg = this._parseErrors(json);
      this.showError(errorTarget, msg);
      return null;
    }
    return json;
  },

  _parseErrors(json) {
    if (typeof json === 'string') return json;
    if (Array.isArray(json))     return json.join(' ');
    if (typeof json === 'object') {
      return Object.entries(json)
        .map(([k, v]) => {
          const vals = Array.isArray(v) ? v : [v];
          // skip technical key names for non_field_errors
          if (k === 'non_field_errors' || k === 'detail') return vals.join(' ');
          return vals.join(' ');
        })
        .join('  ');
    }
    return String(json);
  },

  // Show error inline under a form (pass element id string) or as toast
  showError(targetId, msg) {
    if (targetId) {
      const el = document.getElementById(targetId);
      if (el) { el.textContent = msg; el.style.display = 'block'; return; }
    }
    this.toast(msg, 'error');
  },

  clearError(targetId) {
    const el = document.getElementById(targetId);
    if (el) { el.textContent = ''; el.style.display = 'none'; }
  },

  // Toast notification (top-right)
  toast(msg, type = 'info') {
    const c = document.getElementById('toast-container');
    if (!c) return;
    const t = document.createElement('div');
    t.className = 'toast toast-' + type;
    t.textContent = msg;
    c.appendChild(t);
    setTimeout(() => t.classList.add('toast-show'), 10);
    setTimeout(() => { t.classList.remove('toast-show'); setTimeout(() => t.remove(), 400); }, 4000);
  },

  // --------------------------------------------------
  // LOADING
  // --------------------------------------------------
  loading(show) {
    document.getElementById('loading-overlay').style.display = show ? 'flex' : 'none';
  },

  // --------------------------------------------------
  // LOGIN
  // --------------------------------------------------
  async handleLogin() {
    this.clearError('error-login');
    const phone    = document.getElementById('login-phone').value.trim();
    const password = document.getElementById('login-password').value.trim();
    if (!phone || !password) {
      this.showError('error-login', 'Please enter your phone number and password.');
      return;
    }

    this.loading(true);
    const res = await this.api('/auth/login/', 'POST', { phone, password }, 'error-login');
    this.loading(false);

    if (res && res.access) {
      localStorage.setItem('access_token',  res.access);
      localStorage.setItem('refresh_token', res.refresh);
      localStorage.setItem('user_id',       res.user_id);
      localStorage.setItem('username',      res.username);
      localStorage.setItem('role',          res.role);
      localStorage.setItem('phone',         res.phone || phone);
      localStorage.setItem('first_name',    res.first_name || '');
      localStorage.setItem('last_name',     res.last_name  || '');
      this.enterApp();
    }
  },

  // --------------------------------------------------
  // PASSENGER SIGNUP
  // Auto-generates username from phone so users never
  // see a "username taken" error for a display field.
  // --------------------------------------------------
  async handlePassengerSignup() {
    this.clearError('error-signup-pass');
    const phone      = document.getElementById('signup-pass-phone').value.trim();
    const first_name = document.getElementById('signup-pass-first').value.trim();
    const last_name  = document.getElementById('signup-pass-last').value.trim();
    const password   = document.getElementById('signup-pass-password').value.trim();
    const password2  = document.getElementById('signup-pass-password2').value.trim();

    if (!phone || !password || !password2) {
      this.showError('error-signup-pass', 'Phone number and password are required.');
      return;
    }
    if (password !== password2) {
      this.showError('error-signup-pass', 'Passwords do not match.');
      return;
    }

    // Auto-generate username from phone digits so it is unique but invisible to user
    const username = 'u' + phone.replace(/\D/g, '');

    this.loading(true);
    const res = await this.api('/auth/register/passenger/', 'POST',
      { username, phone, first_name, last_name, password, password2 },
      'error-signup-pass'
    );
    this.loading(false);

    if (res && res.access) {
      localStorage.setItem('access_token',  res.access);
      localStorage.setItem('refresh_token', res.refresh);
      localStorage.setItem('user_id',       res.user_id);
      localStorage.setItem('username',      res.username);
      localStorage.setItem('role',          res.role);
      localStorage.setItem('phone',         res.phone || phone);
      localStorage.setItem('first_name',    res.first_name || first_name);
      localStorage.setItem('last_name',     res.last_name  || last_name);
      this.enterApp();
    }
  },

  // --------------------------------------------------
  // DRIVER SIGNUP
  // --------------------------------------------------
  async handleDriverSignup() {
    this.clearError('error-signup-driver');
    const phone           = document.getElementById('signup-driver-phone').value.trim();
    const first_name      = document.getElementById('signup-driver-first').value.trim();
    const last_name       = document.getElementById('signup-driver-last').value.trim();
    const password        = document.getElementById('signup-driver-password').value.trim();
    const password2       = document.getElementById('signup-driver-password2').value.trim();
    const transport_model = document.getElementById('signup-driver-model').value.trim();
    const transport_year  = parseInt(document.getElementById('signup-driver-year').value);
    const transport_type  = document.getElementById('signup-driver-type').value;
    const from_province   = document.getElementById('signup-driver-from').value.trim();
    const to_province     = document.getElementById('signup-driver-to').value.trim();

    if (!phone || !password || !password2) {
      this.showError('error-signup-driver', 'Phone number and password are required.');
      return;
    }
    if (!transport_model || !transport_year || !transport_type || !from_province || !to_province) {
      this.showError('error-signup-driver', 'Please fill in all vehicle information fields.');
      return;
    }
    if (password !== password2) {
      this.showError('error-signup-driver', 'Passwords do not match.');
      return;
    }
    if (from_province === to_province) {
      this.showError('error-signup-driver', 'From and To province cannot be the same.');
      return;
    }

    // Auto-generate unique username from phone digits
    const username = 'u' + phone.replace(/\D/g, '');

    this.loading(true);
    const res = await this.api('/auth/register/driver/', 'POST', {
      username, phone, first_name, last_name, password, password2,
      transport_model, transport_year, transport_type, from_province, to_province,
    }, 'error-signup-driver');
    this.loading(false);

    if (res && res.access) {
      localStorage.setItem('access_token',  res.access);
      localStorage.setItem('refresh_token', res.refresh);
      localStorage.setItem('user_id',       res.user_id);
      localStorage.setItem('username',      res.username);
      localStorage.setItem('role',          res.role);
      localStorage.setItem('phone',         res.phone || phone);
      localStorage.setItem('first_name',    res.first_name || first_name);
      localStorage.setItem('last_name',     res.last_name  || last_name);
      this.enterApp();
    }
  },

  // --------------------------------------------------
  // LOGOUT
  // --------------------------------------------------
  handleLogout() {
    ['access_token','refresh_token','user_id','username','role','phone','first_name','last_name'].forEach(k => localStorage.removeItem(k));
    this.currentUser = null;
    this.currentRide = null;
    this._resetBooking();
    if (this.locationPollTimer) clearTimeout(this.locationPollTimer);
    this.showAuthView('login');
  },

  // Wipe every booking form field and return to step 1
  _resetBooking() {
    this.selectedTransport = null;
    this._searchResults    = [];
    this._bookProofImages  = [];
    this._bookProofActive  = 0;
    const sel = (id) => document.getElementById(id);
    if (sel('book-from-province')) sel('book-from-province').value = '';
    if (sel('book-to-province'))   sel('book-to-province').value   = '';
    if (sel('book-car-type'))      sel('book-car-type').value      = '';
    if (sel('book-seat'))          sel('book-seat').value          = 'FRONT';
    if (sel('book-payment'))       sel('book-payment').value       = 'cash';
    const results = sel('available-rides');
    if (results) results.innerHTML = '';
    const proof = sel('book-driver-proof');
    if (proof) proof.style.display = 'none';
    if (sel('book-step-1')) this.goToBookStep(1);
  },

  // --------------------------------------------------
  // BOOK: SEARCH
  // --------------------------------------------------
  async searchRides() {
    const from    = document.getElementById('book-from-province').value;
    const to      = document.getElementById('book-to-province').value;
    const carType = document.getElementById('book-car-type').value;

    let qs = '/rides/search/?';
    if (from)    qs += 'from_province=' + from + '&';
    if (to)      qs += 'to_province='   + to   + '&';
    if (carType) qs += 'car_type='      + carType + '&';

    this.loading(true);
    const res = await this.api(qs.replace(/&$/, ''));
    this.loading(false);

    if (!res) return;
    const rides = res.results || res;

    const container = document.getElementById('available-rides');
    if (!rides.length) {
      container.innerHTML = '<p style="color:var(--text-dim);">No rides found for these filters.</p>';
      this.goToBookStep(2);
      return;
    }

    container.innerHTML = rides.map((t, i) => `
      <div class="ride-option" onclick="app.selectTransport(this, ${i})" data-index="${i}">
        <div class="ride-icon">${t.type === 'LUXURY' ? '🏎️' : t.type === 'COMFORT' ? '🚙' : '🚗'}</div>
        <div class="ride-info">
          <h4>${t.driver}</h4>
          <p>${t.model} · ${t.type}</p>
          <p style="font-size:11px;color:var(--text-dim);">${app._provinceName(t.from_province)} → ${app._provinceName(t.to_province)}</p>
        </div>
        <div>
          <div class="ride-price">★ ${t.driver_rating ?? '—'}</div>
        </div>
      </div>
    `).join('');

    this._searchResults = rides;
    this.goToBookStep(2);
  },

  selectTransport(el, index) {
    document.querySelectorAll('#available-rides .ride-option').forEach(r => r.classList.remove('selected'));
    el.classList.add('selected');
    this.selectedTransport = this._searchResults[index];

    const t = this.selectedTransport;
    document.getElementById('book-confirm-details').innerHTML = `
      <div style="display:flex;align-items:center;gap:10px;margin-bottom:12px;">
        <span style="width:8px;height:8px;border-radius:50%;background:var(--green);flex-shrink:0;"></span>
        <span style="font-size:14px;">From: ${app._provinceName(t.from_province)}</span>
      </div>
      <div style="display:flex;align-items:center;gap:10px;margin-bottom:20px;">
        <span style="width:8px;height:8px;border-radius:50%;background:var(--accent);flex-shrink:0;"></span>
        <span style="font-size:14px;">To: ${app._provinceName(t.to_province)}</span>
      </div>
      <div style="display:flex;justify-content:space-between;padding:10px 0;border-bottom:1px solid var(--border);font-size:14px;">
        <span style="color:var(--text-dim);">Driver</span><strong>${t.driver}</strong>
      </div>
      <div style="display:flex;justify-content:space-between;padding:10px 0;border-bottom:1px solid var(--border);font-size:14px;">
        <span style="color:var(--text-dim);">Vehicle</span><strong>${t.model} (${t.type})</strong>
      </div>
      <div style="display:flex;justify-content:space-between;padding:10px 0;font-size:14px;">
        <span style="color:var(--text-dim);">Rating</span><strong>★ ${t.driver_rating ?? '—'}</strong>
      </div>
    `;

    this.renderBookDriverProof(t);

    this.goToBookStep(3);
  },

  renderBookDriverProof(transport) {
    const panel = document.getElementById('book-driver-proof');
    const badgesEl = document.getElementById('book-driver-badges');
    const countEl = document.getElementById('book-driver-verified-count');
    const mainWrap = document.getElementById('book-driver-main-image-wrap');
    const mainImg = document.getElementById('book-driver-main-image');
    const imagesEl = document.getElementById('book-driver-images');

    if (!panel || !badgesEl || !countEl || !mainWrap || !mainImg || !imagesEl) return;

    const badges = transport?.verification_badges || {};
    const verifiedCount =
      (badges.license_with_id_verified ? 1 : 0) +
      (badges.vehicle_registration_verified ? 1 : 0);
    countEl.textContent = verifiedCount + '/2 verified';

    const licSvg = badges.license_with_id_verified
      ? '<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>'
      : '';
    const regSvg = badges.vehicle_registration_verified
      ? '<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>'
      : '';
    badgesEl.innerHTML = `
      <span class="doc-badge ${badges.license_with_id_verified ? 'doc-badge--approved' : 'doc-badge--pending'}">${licSvg} License &amp; ID</span>
      <span class="doc-badge ${badges.vehicle_registration_verified ? 'doc-badge--approved' : 'doc-badge--pending'}">${regSvg} Tech Passport</span>
    `;

    const photos = Array.isArray(transport?.car_images) ? transport.car_images : [];
    this._bookProofImages = photos;
    this._bookProofActive = 0;

    if (!photos.length) {
      mainWrap.style.display = 'none';
      imagesEl.style.display = 'none';
      imagesEl.innerHTML = '';
    } else {
      mainImg.src = photos[0].url;
      mainWrap.style.display = 'block';
      if (photos.length > 1) {
        imagesEl.style.display = 'flex';
        imagesEl.innerHTML = photos
          .map((p, i) => `
            <button type="button" class="driver-proof-thumb ${i === 0 ? 'is-active' : ''}" onclick="app.selectBookProofImage(${i})">
              <img src="${p.url}" alt="Driver car photo ${i + 1}" loading="lazy">
            </button>
          `)
          .join('');
      } else {
        imagesEl.style.display = 'none';
        imagesEl.innerHTML = '';
      }
    }

    panel.style.display = 'block';
  },

  selectBookProofImage(index) {
    const photos = this._bookProofImages || [];
    if (!photos[index]) return;

    this._bookProofActive = index;
    const mainImg = document.getElementById('book-driver-main-image');
    if (mainImg) mainImg.src = photos[index].url;

    document.querySelectorAll('#book-driver-images .driver-proof-thumb').forEach((el, i) => {
      el.classList.toggle('is-active', i === index);
    });
  },

  goToBookStep(n) {
    [1, 2, 3].forEach(i => {
      document.getElementById('book-step-' + i).style.display = i === n ? 'block' : 'none';
      const dot = document.getElementById('step' + i + '-dot');
      if (dot) dot.classList.toggle('active', i <= n);
    });
  },

  // Province value → human-readable label
  _provinceName(val) {
    if (!val) return '—';
    return val.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
  },

  async confirmAndBook() {
    if (!this.selectedTransport) { this.toast('Please select a ride first.', 'error'); return; }

    const seat    = document.getElementById('book-seat').value;
    const payment = document.getElementById('book-payment').value;
    const t       = this.selectedTransport;

    if (!t.driver_id) {
      this.toast('Selected driver data is invalid. Please search again.', 'error');
      return;
    }

    const depTime = new Date();
    depTime.setHours(depTime.getHours() + 1);

    this.loading(true);
    const res = await this.api('/rides/', 'POST', {
      driver:          t.driver_id,
      route:           t.route || null,
      from_province:   t.from_province,
      to_province:     t.to_province,
      seat,
      departure_time:  depTime.toISOString(),
      price:           '0.00',
      payment_method:  payment,
      payment_status:  'unpaid',
    });
    this.loading(false);

    if (res && res.id) {
      this.toast('Ride booked! Go to Track to follow your ride.', 'success');
      this.currentRide = res;
      this.showView('track');
    }
  },

  // --------------------------------------------------
  // TRACK: ACTIVE RIDE
  // --------------------------------------------------
  async loadActiveRide() {
    this.loading(true);
    const res = await this.api('/rides/?status=in_progress');
    if (!res) { this.loading(false); return; }

    const rides = res.results || res;

    if (!rides.length) {
      // Also check pending / confirmed
      const res2 = await this.api('/rides/?status=pending');
      const res3 = await this.api('/rides/?status=confirmed');
      const all = [...(res2?.results || []), ...(res3?.results || [])];
      this.loading(false);
      if (all.length) {
        this.currentRide = all[0];
        this.renderActiveRide();
      } else {
        this.renderNoRide();
      }
    } else {
      this.loading(false);
      this.currentRide = rides[0];
      this.renderActiveRide();
    }
  },

  renderNoRide() {
    document.getElementById('no-active-ride').style.display = 'block';
    document.getElementById('active-ride-info').style.display = 'none';
    document.getElementById('driver-status-card').style.display = 'none';
    document.getElementById('chat-section').style.display = 'none';
    document.getElementById('ride-actions').style.display = 'none';
  },

  renderActiveRide() {
    const r = this.currentRide;
    document.getElementById('no-active-ride').style.display = 'none';
    document.getElementById('active-ride-info').style.display = 'block';
    document.getElementById('chat-section').style.display = 'block';
    document.getElementById('ride-actions').style.display = 'flex';

    // Driver card
    const driverCard = document.getElementById('driver-status-card');
    driverCard.style.display = 'flex';
    document.getElementById('driver-avatar-initials').textContent = r.driver ? r.driver.slice(0, 2).toUpperCase() : '--';
    document.getElementById('driver-name').textContent = r.driver || 'Driver';
    document.getElementById('driver-vehicle').textContent = 'Seat: ' + r.seat;
    document.getElementById('driver-rating').textContent = '★ —';

    // Route
    document.getElementById('ride-status-display').textContent = r.status.replace('_', ' ').toUpperCase();
    document.getElementById('ride-from').textContent = 'Province ' + r.from_province;
    document.getElementById('ride-to').textContent   = 'Province ' + r.to_province;
    document.getElementById('ride-departure').textContent = new Date(r.departure_time).toLocaleString();

    // Map
    this.initTrackingMap();
    this.pollLocation();

    // Chat
    this.loadChatMessages();
  },

  // --------------------------------------------------
  // TRACKING MAP
  // --------------------------------------------------
  initTrackingMap() {
    if (this.trackingMap) { this.trackingMap.remove(); this.trackingMap = null; }
    const el = document.getElementById('tracking-map');
    if (!el) return;
    this.trackingMap = L.map('tracking-map').setView([41.0, 69.0], 10);
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      attribution: '© OpenStreetMap contributors', maxZoom: 19,
    }).addTo(this.trackingMap);
  },

  pollLocation() {
    if (!this.currentRide) return;
    this.loadLatestLocation();
    this.locationPollTimer = setTimeout(() => this.pollLocation(), 5000);
  },

  async loadLatestLocation() {
    if (!this.currentRide || !this.trackingMap) return;
    const loc = await this.api('/rides/' + this.currentRide.id + '/locations/latest/');
    if (loc && loc.latitude != null) {
      const lat = parseFloat(loc.latitude);
      const lng = parseFloat(loc.longitude);
      this.trackingMap.setView([lat, lng], 15);
      if (this.driverMarker) this.trackingMap.removeLayer(this.driverMarker);
      this.driverMarker = L.marker([lat, lng])
        .addTo(this.trackingMap)
        .bindPopup('<strong>' + (loc.driver || 'Driver') + '</strong><br>Live location');
    }
  },

  // --------------------------------------------------
  // CHAT
  // --------------------------------------------------
  async loadChatMessages() {
    if (!this.currentRide) return;
    const res = await this.api('/rides/' + this.currentRide.id + '/messages/');
    if (!res) return;

    const msgs = res.results || res;
    const container = document.getElementById('chat-messages');
    const myId = parseInt(localStorage.getItem('user_id'));

    container.innerHTML = msgs.map(m => `
      <div class="chat-message ${m.sender_id === myId ? 'own' : 'other'}">
        <div class="msg-content">
          <div class="msg-sender">${m.sender}</div>
          <div class="msg-text">${m.message}</div>
          <div class="msg-time">${new Date(m.timestamp).toLocaleTimeString([], {hour:'2-digit',minute:'2-digit'})}</div>
        </div>
      </div>
    `).join('');

    container.scrollTop = container.scrollHeight;
  },

  async sendChatMessage() {
    if (!this.currentRide) { this.toast('No active ride.', 'error'); return; }
    const input = document.getElementById('chat-input');
    const message = input.value.trim();
    if (!message) return;

    const res = await this.api('/rides/' + this.currentRide.id + '/messages/', 'POST', { message });
    if (res) { input.value = ''; this.loadChatMessages(); }
  },

  // --------------------------------------------------
  // CANCEL RIDE
  // --------------------------------------------------
  async cancelRide() {
    if (!this.currentRide) return;
    if (!confirm('Cancel this ride?')) return;
    this.loading(true);
    const res = await this.api('/rides/' + this.currentRide.id + '/cancel/', 'POST');
    this.loading(false);
    if (res !== null) {
      this.currentRide = null;
      if (this.locationPollTimer) clearTimeout(this.locationPollTimer);
      this.renderNoRide();
    }
  },

  // --------------------------------------------------
  // HISTORY
  // --------------------------------------------------
  async loadRideHistory() {
    this.loading(true);
    const res = await this.api('/rides/');
    this.loading(false);
    if (!res) return;

    const rides = res.results || res;
    const container = document.getElementById('history-list');

    if (!rides.length) {
      container.innerHTML = '<p style="color:var(--text-dim);">No rides yet. Book your first ride!</p>';
      return;
    }

    const statusColor = s => ({ completed:'var(--green)', cancelled:'var(--red)' }[s] || 'var(--text-dim)');

    container.innerHTML = rides.map(r => {
      const isCompleted = r.status === 'completed';
      const hasReport = !!r.lost_item_report_status;
      let actionBtn = '';
      if (isCompleted && !hasReport) {
        actionBtn = `<button class="btn-ghost btn-sm history-action" onclick="app.openLostItemModal(${r.id})">Report Lost Item</button>`;
      } else if (hasReport) {
        const label = r.lost_item_report_status === 'found' ? 'Item found'
          : r.lost_item_report_status === 'not_found' ? 'Not found'
          : 'Report submitted';
        actionBtn = `<span class="history-report-status">${label}</span>`;
      }
      return `
      <div class="history-card">
        <div class="history-date">
          <div class="day">${new Date(r.departure_time).getDate()}</div>
          <div class="month">${new Date(r.departure_time).toLocaleString('default',{month:'short'})}</div>
        </div>
        <div class="history-route">
          <div class="from"><span class="dot-s"></span> From Province ${r.from_province}</div>
          <div class="to"><span class="dot-e"></span> To Province ${r.to_province}</div>
        </div>
        <div class="history-meta">
          <div class="ride-type">Seat: ${r.seat}</div>
          <div class="ride-time" style="color:${statusColor(r.status)}">${r.status.replace('_',' ')}</div>
        </div>
        <div class="history-price">$${r.price}</div>
        ${actionBtn ? `<div class="history-actions">${actionBtn}</div>` : ''}
      </div>
    `;
    }).join('');
  },

  openLostItemModal(rideId) {
    document.getElementById('lost-item-ride-id').value = rideId;
    document.getElementById('lost-item-description').value = '';
    document.getElementById('lost-item-share-contact').checked = false;
    const err = document.getElementById('lost-item-error');
    err.style.display = 'none';
    err.textContent = '';
    document.getElementById('lost-item-modal').style.display = 'flex';
  },

  closeLostItemModal() {
    document.getElementById('lost-item-modal').style.display = 'none';
  },

  async submitLostItemReport(e) {
    e.preventDefault();
    const rideId = document.getElementById('lost-item-ride-id').value;
    const item_description = document.getElementById('lost-item-description').value.trim();
    const share_contact = document.getElementById('lost-item-share-contact').checked;
    const errEl = document.getElementById('lost-item-error');

    if (!item_description) {
      errEl.textContent = 'Please describe the lost item.';
      errEl.style.display = 'block';
      return;
    }

    this.loading(true);
    const res = await this.api('/rides/' + rideId + '/lost-item/', 'POST', {
      item_description,
      share_contact,
    });
    this.loading(false);

    if (res) {
      this.closeLostItemModal();
      this.toast('Lost item report submitted. Your driver has been notified.', 'success');
      this.loadRideHistory();
    } else {
      errEl.textContent = 'Could not submit report. It may already exist for this ride.';
      errEl.style.display = 'block';
    }
  },

  _startLostItemPolling() {
    if (this.lostItemPollTimer) clearInterval(this.lostItemPollTimer);
    if (localStorage.getItem('role') !== 'DRIVER') return;

    const poll = () => this.checkDriverLostItemReports();
    poll();
    this.lostItemPollTimer = setInterval(poll, 30000);
  },

  async checkDriverLostItemReports() {
    if (localStorage.getItem('role') !== 'DRIVER') return;
    const reports = await this.api('/drivers/lost-item-reports/');
    if (!reports || !reports.length) return;

    reports.forEach(report => {
      if (this._seenLostItemIds.has(report.id)) return;
      this._seenLostItemIds.add(report.id);
      this.toast(report.notification_message, 'info');
    });

    if (document.getElementById('view-profile').classList.contains('active')) {
      this._renderDriverLostItems(reports);
    }
  },

  async respondToLostItem(rideId, response) {
    this.loading(true);
    const res = await this.api('/rides/' + rideId + '/lost-item/respond/', 'PATCH', {
      driver_response: response,
    });
    this.loading(false);

    if (res) {
      const msg = response === 'yes'
        ? 'Thanks! The passenger will be notified that you found the item.'
        : 'Response recorded. The passenger has been notified.';
      this.toast(msg, 'success');
      const reports = await this.api('/drivers/lost-item-reports/');
      this._renderDriverLostItems(reports || []);
    } else {
      this.toast('Could not submit your response.', 'error');
    }
  },

  _renderDriverLostItems(reports) {
    const card = document.getElementById('profile-lost-items-card');
    const list = document.getElementById('profile-lost-items-list');
    if (!card || !list) return;

    if (!reports.length) {
      card.style.display = localStorage.getItem('role') === 'DRIVER' ? 'block' : 'none';
      list.innerHTML = '<p style="color:var(--text-dim);font-size:14px;margin:0;">No pending reports.</p>';
      return;
    }

    card.style.display = 'block';
    list.innerHTML = reports.map(r => `
      <div class="lost-item-alert">
        <p class="lost-item-message">${r.notification_message}</p>
        ${r.share_contact && r.passenger_contact ? `<p class="lost-item-contact">Passenger contact: ${r.passenger_contact}</p>` : ''}
        <div class="lost-item-actions">
          <button class="btn-primary btn-sm" onclick="app.respondToLostItem(${r.ride}, 'yes')">Yes, I have it</button>
          <button class="btn-ghost btn-sm" onclick="app.respondToLostItem(${r.ride}, 'no')">No, I couldn't find it</button>
        </div>
      </div>
    `).join('');
  },

  // --------------------------------------------------
  // PROFILE
  // --------------------------------------------------
  async loadProfile() {
    const role       = localStorage.getItem('role') || 'PASSENGER';
    const firstName  = localStorage.getItem('first_name') || '';
    const lastName   = localStorage.getItem('last_name')  || '';
    const phone      = localStorage.getItem('phone') || '';

    // Build display name — fallback to phone if no name provided
    const displayName = [firstName, lastName].filter(Boolean).join(' ') || phone || '—';
    // Initials from real name (or first 2 chars of phone)
    const initials = firstName && lastName
      ? (firstName[0] + lastName[0]).toUpperCase()
      : (firstName ? firstName.slice(0, 2).toUpperCase() : (phone.replace(/\D/g, '').slice(-2) || '--'));

    // ── Always reset driver-only DOM sections first ──────────────────────────
    // This prevents data from a previous driver session leaking into a passenger view
    document.getElementById('online-toggle-btn').style.display        = 'none';
    document.getElementById('profile-rating-pill').style.display      = 'none';
    document.getElementById('profile-vehicle-card').style.display     = 'none';
    document.getElementById('profile-docs-card').style.display        = 'none';
    document.getElementById('profile-lost-items-card').style.display  = 'none';

    document.getElementById('profile-online-bar').classList.remove('active');
    document.getElementById('profile-identity-card').classList.remove('profile-identity-card--online');
    // ── Always reset passenger-only DOM sections ─────────────────────────────
    const passengerSection = document.getElementById('profile-passenger-section');
    if (passengerSection) passengerSection.style.display = 'none';

    // Populate identity card
    const h3  = document.getElementById('profile-username');
    const pill = document.getElementById('profile-rating-pill');
    h3.textContent = displayName + ' ';
    h3.appendChild(pill);
    document.getElementById('profile-avatar-initials').textContent = initials;
    document.getElementById('profile-phone').textContent = phone;
    document.getElementById('profile-role-text').textContent = role === 'DRIVER' ? 'Pro Driver' : 'Passenger';

    this.loading(true);
    try {

      if (role === 'DRIVER') {
        const [profileRes, statsRes, docsRes] = await Promise.all([
          this.api('/drivers/me/'),
          this.api('/drivers/stats/'),
          this.api('/driver/documents/'),
        ]);

        if (profileRes) {
          const rating = profileRes.avg_rating ?? 0;
          document.getElementById('profile-rating-val').textContent = Number(rating).toFixed(1);
          document.getElementById('profile-rating-pill').style.display = 'inline-flex';

          this._driverIsOnline = !!profileRes.is_online;
          this._updateOnlineToggle(this._driverIsOnline);
          document.getElementById('online-toggle-btn').style.display = 'inline-flex';

          if (profileRes.transport) {
            const t = profileRes.transport;
            document.getElementById('vehicle-model').textContent   = t.model + ' ' + (t.year || '');
            document.getElementById('vehicle-details').textContent = t.type + ' • ' + t.from_province + ' → ' + t.to_province;
            document.getElementById('profile-vehicle-card').style.display = 'flex';
          }
        }

        if (statsRes) {
          document.getElementById('stat-total-rides').textContent = statsRes.total_rides ?? 0;
          document.getElementById('stat-completed').textContent   = statsRes.completed ?? 0;
          document.getElementById('stat-extra').textContent       = '$' + (statsRes.total_earnings ?? 0);
          document.getElementById('stat-extra-label').textContent = 'Total Earnings';
        }



        if (docsRes !== null) {
          document.getElementById('profile-docs-card').style.display = 'block';
          const docsArray = Array.isArray(docsRes) ? docsRes : (docsRes.results || []);
          this._renderDocuments(docsArray);
        }

        const lostItemsRes = await this.api('/drivers/lost-item-reports/');
        if (lostItemsRes) this._renderDriverLostItems(lostItemsRes);

      } else {
        // ── Passenger layout ────────────────────────────────────────────────
        if (passengerSection) passengerSection.style.display = 'block';

        const statsRes = await this.api('/passengers/stats/');
        if (statsRes) {
          document.getElementById('stat-total-rides').textContent = statsRes.total_rides ?? 0;
          document.getElementById('stat-completed').textContent   = statsRes.completed ?? 0;
          document.getElementById('stat-extra').textContent       = '$' + (statsRes.total_spent ?? 0);
          document.getElementById('stat-extra-label').textContent = 'Total Spent';
        }
      }

    } catch (e) {
      console.error('Profile load error:', e);
      this.toast('Could not load profile data.', 'error');
    } finally {
      this.loading(false);
    }
  },

  _updateOnlineToggle(isOnline) {
    const btn   = document.getElementById('online-toggle-btn');
    const label = document.getElementById('online-toggle-label');
    const bar   = document.getElementById('profile-online-bar');
    const card  = document.getElementById('profile-identity-card');

    label.textContent = isOnline ? 'GO OFFLINE' : 'GO ONLINE';
    btn.classList.toggle('online-toggle-btn--online', isOnline);
    bar.classList.toggle('active', isOnline);
    card.classList.toggle('profile-identity-card--online', isOnline);
  },

  async toggleOnline() {
    this._driverIsOnline = !this._driverIsOnline;
    this._updateOnlineToggle(this._driverIsOnline);
    const res = await this.api('/drivers/me/', 'PATCH', { is_online: this._driverIsOnline });
    if (!res) {
      // revert on failure
      this._driverIsOnline = !this._driverIsOnline;
      this._updateOnlineToggle(this._driverIsOnline);
      this.toast('Failed to update status', 'error');
    } else {
      this.toast(this._driverIsOnline ? 'You are now online — ready for trips!' : 'You are now offline.', 'info');
    }
  },

  _renderDocuments(docs) {
    const DOC_LABELS = {
      LICENSE_WITH_ID:      'Driver License & ID Card',
      VEHICLE_REGISTRATION: 'Vehicle Registration (Tech Passport)',
      CAR_PHOTO:            'Car Interior / Exterior Photo',
    };

    // All known doc types for this app
    const ALL_DOC_TYPES = ['LICENSE_WITH_ID', 'VEHICLE_REGISTRATION', 'CAR_PHOTO'];
    const list = document.getElementById('profile-docs-list');
    list.innerHTML = '';

    let hasMissing = false;

    ALL_DOC_TYPES.forEach(type => {
      const found = docs.find(d => d.doc_type === type);
      const label = DOC_LABELS[type] || type;
      const item  = document.createElement('div');
      item.className = 'doc-item';

      if (!found) {
        hasMissing = true;
        item.className += ' doc-item--missing';
        item.innerHTML = `
          <div class="doc-item-left">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>
            <span>${label}</span>
          </div>
          <button class="doc-badge doc-badge--missing" onclick="app._triggerDocUpload('${type}')">Upload Now</button>`;
      } else if (found.status === 'APPROVED') {
        item.innerHTML = `
          <div class="doc-item-left">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>
            <span>${label}</span>
          </div>
          <span class="doc-badge doc-badge--approved">
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>
            Verified
          </span>`;
      } else if (found.status === 'REJECTED') {
        hasMissing = true;
        item.className += ' doc-item--missing';
        item.innerHTML = `
          <div class="doc-item-left">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>
            <span>${label}<small style="color:var(--red);margin-left:6px;">${found.admin_note ? '— ' + found.admin_note : ''}</small></span>
          </div>
          <button class="doc-badge doc-badge--missing" onclick="app._triggerDocUpload('${type}')">Re-upload</button>`;
      } else {
        // PENDING
        item.innerHTML = `
          <div class="doc-item-left">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>
            <span>${label}</span>
          </div>
          <span class="doc-badge doc-badge--pending">
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>
            Reviewing
          </span>`;
      }

      list.appendChild(item);
    });

    if (hasMissing) {
      document.getElementById('doc-upload-area').style.display = 'block';
    }
  },

  _currentUploadDocType: null,
  _triggerDocUpload(docType) {
    this._currentUploadDocType = docType;
    document.getElementById('doc-file-input').click();
  },

  async uploadDocument(input) {
    const file = input.files[0];
    if (!file) return;

    const docType = this._currentUploadDocType || 'LICENSE_WITH_ID';
    const token   = localStorage.getItem('access_token');

    const form = new FormData();
    form.append('file', file);
    form.append('doc_type', docType);

    this.loading(true);
    try {
      const res = await fetch('/api/driver/documents/', {
        method: 'POST',
        headers: { Authorization: 'Bearer ' + token },
        body: form,
      });
      if (res.ok) {
        this.toast('Document uploaded — under review.', 'success');
        // reload documents section
        const docs = await this.api('/driver/documents/');
        if (docs) this._renderDocuments(Array.isArray(docs) ? docs : (docs.results || []));
        document.getElementById('doc-upload-area').style.display = 'none';
      } else {
        const err = await res.json().catch(() => ({}));
        this.toast(this._parseErrors(err) || 'Upload failed.', 'error');
      }
    } catch (e) {
      this.toast('Upload failed — check your connection.', 'error');
    }
    this.loading(false);
    input.value = '';
  },


};

document.addEventListener('DOMContentLoaded', () => app.init());
