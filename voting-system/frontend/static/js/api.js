const API = {
  base: "http://127.0.0.1:5000",

  async post(endpoint, data) {
    const res = await fetch(this.base + endpoint, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "include",
      body: JSON.stringify(data)
    });
    return res.json();
  },

  async get(endpoint) {
    const res = await fetch(this.base + endpoint, { credentials: "include" });
    return res.json();
  }
};

const Camera = {
  stream: null,

  async start(videoEl) {
    try {
      // Try high quality first, fall back to basic constraints if needed
      const constraints = [
        { video: { width: { ideal: 1280 }, height: { ideal: 720 }, facingMode: "user" } },
        { video: { width: { ideal: 640 }, height: { ideal: 480 }, facingMode: "user" } },
        { video: true }
      ];

      let lastError = null;
      for (const c of constraints) {
        try {
          this.stream = await navigator.mediaDevices.getUserMedia(c);
          break;
        } catch (e) {
          lastError = e;
          this.stream = null;
        }
      }

      if (!this.stream) throw lastError;

      videoEl.srcObject = this.stream;

      // Wait for video metadata to load so dimensions are available
      await new Promise((resolve, reject) => {
        videoEl.onloadedmetadata = () => resolve();
        videoEl.onerror = (e) => reject(e);
        setTimeout(resolve, 3000); // fallback timeout
      });

      await videoEl.play();
      return true;
    } catch (e) {
      console.error("Camera error:", e);
      return false;
    }
  },

  capture(videoEl, canvasEl) {
    // Use actual video dimensions, with safe fallbacks
    const w = videoEl.videoWidth  > 0 ? videoEl.videoWidth  : 640;
    const h = videoEl.videoHeight > 0 ? videoEl.videoHeight : 480;
    canvasEl.width  = w;
    canvasEl.height = h;
    const ctx = canvasEl.getContext("2d");
    ctx.drawImage(videoEl, 0, 0, w, h);
    // Use higher quality JPEG for better face detection
    return canvasEl.toDataURL("image/jpeg", 0.95);
  },

  stop() {
    if (this.stream) {
      this.stream.getTracks().forEach(t => t.stop());
      this.stream = null;
    }
  }
};

function showToast(msg, type = "info") {
  const existing = document.querySelector(".toast-container");
  if (existing) existing.remove();

  const icons = { success: "✅", danger: "❌", info: "ℹ️", warning: "⚠️" };
  const wrap = document.createElement("div");
  wrap.className = "toast-container";
  wrap.style.cssText = `
    position:fixed; top:20px; left:50%; transform:translateX(-50%);
    z-index:9999; animation: slideDown 0.3s ease;
  `;
  wrap.innerHTML = `
    <div class="alert alert-${type}" style="min-width:280px; box-shadow:0 8px 32px rgba(0,0,0,0.15);">
      ${icons[type] || ""} ${msg}
    </div>`;
  document.body.appendChild(wrap);
  setTimeout(() => wrap.remove(), 4000);
}

async function requireAuth(adminOnly = false) {
  const data = await API.get("/api/session");
  if (!data.logged_in) { window.location.href = "/login"; return null; }
  if (adminOnly && !data.is_admin) { window.location.href = "/home"; return null; }
  return data;
}