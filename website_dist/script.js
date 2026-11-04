// Circuit Verse Portal Client Script

document.addEventListener("DOMContentLoaded", () => {
  // 1. Mobile Menu Toggle
  const mobileBtn = document.querySelector(".mobile-menu-btn");
  const navLinks = document.querySelector(".nav-links");
  if (mobileBtn && navLinks) {
    mobileBtn.addEventListener("click", () => {
      navLinks.classList.toggle("open");
    });
  }

  // 2. Copy to Clipboard
  const copyButtons = document.querySelectorAll(".copy-btn");
  copyButtons.forEach((btn) => {
    btn.addEventListener("click", () => {
      const textToCopy = btn.getAttribute("data-copy");
      if (textToCopy) {
        navigator.clipboard.writeText(textToCopy).then(() => {
          const originalText = btn.innerHTML;
          btn.innerHTML = `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="20 6 9 17 4 12"></polyline></svg> Copied!`;
          btn.style.borderColor = "var(--accent-green)";
          btn.style.color = "var(--accent-green)";
          setTimeout(() => {
            btn.innerHTML = originalText;
            btn.style.borderColor = "";
            btn.style.color = "";
          }, 2000);
        });
      }
    });
  });

  // 3. Radio Live Stream Player
  const audio = document.getElementById("radio-audio");
  const playBtn = document.getElementById("play-toggle-btn");
  const playIcon = document.getElementById("play-icon");
  const volumeSlider = document.getElementById("volume-slider");
  const trackTitle = document.getElementById("track-title");
  const trackArtist = document.getElementById("track-artist");
  const trackArt = document.getElementById("track-art");
  const listenerCount = document.getElementById("radio-listeners-badge");

  const STREAM_URL = "https://radio.circuitverse.online/listen/circuit_verse_radio/radio.mp3";
  const NOWPLAYING_API = "https://radio.circuitverse.online/api/nowplaying/circuit_verse_radio";

  let isPlaying = false;

  if (playBtn && audio) {
    playBtn.addEventListener("click", () => {
      if (!isPlaying) {
        audio.src = STREAM_URL + "?cachebust=" + Date.now();
        audio.play().then(() => {
          isPlaying = true;
          updatePlayButton();
        }).catch(err => {
          console.error("Playback error:", err);
        });
      } else {
        audio.pause();
        audio.src = "";
        isPlaying = false;
        updatePlayButton();
      }
    });
  }

  function updatePlayButton() {
    if (isPlaying) {
      playIcon.innerHTML = `<svg width="24" height="24" viewBox="0 0 24 24" fill="currentColor"><rect x="6" y="4" width="4" height="16"></rect><rect x="14" y="4" width="4" height="16"></rect></svg>`;
      playBtn.style.boxShadow = "0 0 30px var(--accent-pink)";
    } else {
      playIcon.innerHTML = `<svg width="24" height="24" viewBox="0 0 24 24" fill="currentColor"><polygon points="5 3 19 12 5 21 5 3"></polygon></svg>`;
      playBtn.style.boxShadow = "var(--glow-cyan)";
    }
  }

  if (volumeSlider && audio) {
    volumeSlider.addEventListener("input", (e) => {
      audio.volume = e.target.value / 100;
    });
  }

  // Fetch Live Radio Metadata
  async function fetchRadioMetadata() {
    try {
      const resp = await fetch(NOWPLAYING_API);
      if (resp.ok) {
        const data = await resp.json();
        const np = data.now_playing;
        if (np && np.song) {
          if (trackTitle) trackTitle.textContent = np.song.title || "Circuit Verse Radio";
          if (trackArtist) trackArtist.textContent = np.song.artist || "24/7 EDM & Synthwave";
          if (trackArt && np.song.art && !np.song.art.includes("generic_song")) {
            trackArt.src = np.song.art;
          }
        }
        if (listenerCount && data.listeners) {
          listenerCount.textContent = `${data.listeners.current || 0} Listening`;
        }
      }
    } catch (e) {
      console.warn("Could not fetch radio metadata:", e);
    }
  }

  fetchRadioMetadata();
  setInterval(fetchRadioMetadata, 10000);

  // 4. Live Minecraft Status Check
  const mcOnlinePill = document.getElementById("mc-status-pill");
  const mcCountPill = document.getElementById("mc-player-count");

  async function checkMinecraftStatus() {
    try {
      const resp = await fetch("https://api.mcsrvstat.us/3/play.circuitverse.online");
      if (resp.ok) {
        const data = await resp.json();
        if (data.online) {
          if (mcOnlinePill) {
            mcOnlinePill.innerHTML = `<span class="pulse-dot" style="background:#10b981;box-shadow:0 0 10px #10b981"></span> Online (v${data.version || "1.21.x"})`;
          }
          if (mcCountPill) {
            mcCountPill.textContent = `${data.players.online}/${data.players.max} Online`;
          }
        }
      }
    } catch (err) {
      console.warn("Minecraft status check:", err);
    }
  }

  checkMinecraftStatus();
  setInterval(checkMinecraftStatus, 30000);
});
