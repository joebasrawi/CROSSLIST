const PREVIEW_ENDPOINT = "/v1/transfers/spotify-to-apple/preview";

const form = document.getElementById("preview-form");
const urlInput = document.getElementById("playlist-url");
const storefrontInput = document.getElementById("storefront");
const submitButton = document.getElementById("submit-button");
const errorEl = document.getElementById("error");
const resultsEl = document.getElementById("results");

function node(tag, attrs = {}, children = []) {
  const el = document.createElement(tag);
  for (const [key, value] of Object.entries(attrs)) {
    if (value == null || value === false) continue;
    if (key === "className") el.className = value;
    else if (key === "text") el.textContent = value;
    else if (key === "htmlFor") el.htmlFor = value;
    else el.setAttribute(key, value);
  }
  for (const child of [].concat(children)) {
    if (child == null || child === false) continue;
    el.append(child.nodeType ? child : document.createTextNode(String(child)));
  }
  return el;
}

function showError(message, hint) {
  resultsEl.hidden = true;
  resultsEl.removeAttribute("data-visible");
  resultsEl.replaceChildren();
  errorEl.hidden = false;
  errorEl.dataset.visible = "true";
  errorEl.replaceChildren(
    node("strong", { text: message }),
    hint ? node("p", { className: "hint", text: hint }) : null,
  );
}

function clearError() {
  errorEl.hidden = true;
  errorEl.removeAttribute("data-visible");
  errorEl.replaceChildren();
}

function artwork(url, className) {
  if (!url) return node("div", { className, "aria-hidden": "true" });
  const img = node("img", {
    className,
    src: url,
    alt: "",
  });
  img.addEventListener("error", () => img.replaceWith(node("div", { className })));
  return img;
}

function percent(value) {
  return `${Math.round(Number(value) * 100)}%`;
}

function methodLabel(method) {
  return method === "isrc" ? "ISRC match" : "Metadata match";
}

function renderResults(preview) {
  const matched = preview.tracks.filter((track) => track.status === "matched");
  const skipped = preview.tracks.filter((track) => track.status !== "matched");

  const header = node("div", { className: "playlist" }, [
    artwork(preview.playlist.artwork_url, "artwork"),
    node("div", {}, [
      node("h2", { text: preview.playlist.name }),
      node("p", {
        text: `${preview.matched_count} of ${preview.tracks.length} songs matched`,
      }),
    ]),
  ]);

  const skipBanner =
    preview.unmatched_count > 0
      ? node("p", {
          className: "skip-banner",
          text: `${preview.unmatched_count} ${
            preview.unmatched_count === 1 ? "song" : "songs"
          } skipped for a low-confidence or missing Apple Music match.`,
        })
      : null;

  const matchSection = [
    node("p", { className: "section-label", text: "APPLE MUSIC MATCHES" }),
    matched.length
      ? node(
          "ol",
          { className: "track-list" },
          matched.map((track) => {
            const match = track.match;
            return node("li", { className: "track" }, [
              node("span", { className: "position", text: String(track.source.position + 1) }),
              artwork(match.artwork_url || track.source.artwork_url, "thumb"),
              node("div", { className: "track-copy" }, [
                node("strong", { text: match.name }),
                node("span", {
                  text: [match.artist, match.album].filter(Boolean).join(" · "),
                }),
                node("div", { className: "badges" }, [
                  node("span", { className: "badge match", text: methodLabel(match.method) }),
                  node("span", { className: "badge", text: percent(match.confidence) }),
                ]),
              ]),
              match.url
                ? node("a", {
                    className: "apple-link",
                    href: match.url,
                    target: "_blank",
                    rel: "noopener noreferrer",
                    text: "Apple Music",
                  })
                : null,
            ]);
          }),
        )
      : node("p", { className: "meta", text: "No Apple Music matches crossed the confidence bar." }),
  ];

  const skipSection = skipped.length
    ? [
        node("p", { className: "section-label", text: "SKIPPED / LOW CONFIDENCE" }),
        node(
          "ol",
          { className: "track-list" },
          skipped.map((track) =>
            node("li", { className: "track" }, [
              node("span", { className: "position", text: String(track.source.position + 1) }),
              artwork(track.source.artwork_url, "thumb"),
              node("div", { className: "track-copy" }, [
                node("strong", { text: track.source.name }),
                node("span", {
                  text: [track.source.artist, track.source.album].filter(Boolean).join(" · "),
                }),
                node("div", { className: "badges" }, [
                  node("span", { className: "badge", text: "Not added" }),
                ]),
              ]),
            ]),
          ),
        ),
      ]
    : [];

  resultsEl.hidden = false;
  resultsEl.dataset.visible = "true";
  resultsEl.replaceChildren(header, skipBanner, ...matchSection, ...skipSection);
}

function parseApiError(payload, status) {
  if (payload && payload.error) {
    return {
      message: payload.error.message || "CROSSLIST could not preview this playlist.",
      hint: payload.error.hint || null,
    };
  }
  if (payload && payload.detail) {
    return {
      message: "That playlist link could not be used.",
      hint: "Paste a public Spotify playlist URL and try again.",
    };
  }
  return {
    message: "CROSSLIST could not preview this playlist.",
    hint: status ? `The server responded with ${status}.` : null,
  };
}

async function loadPreview() {
  const playlistUrl = urlInput.value.trim();
  if (!playlistUrl) {
    showError("Paste a valid public Spotify playlist link.");
    return;
  }

  clearError();
  submitButton.disabled = true;
  submitButton.textContent = "Matching tracks…";

  try {
    const response = await fetch(PREVIEW_ENDPOINT, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "omit",
      body: JSON.stringify({
        playlist_url: playlistUrl,
        storefront: storefrontInput.value || "us",
      }),
    });
    const payload = await response.json().catch(() => null);
    if (!response.ok) {
      const error = parseApiError(payload, response.status);
      showError(error.message, error.hint);
      return;
    }
    renderResults(payload);
  } catch (_err) {
    showError(
      "CROSSLIST could not reach the matching API.",
      "Confirm this page is being served from the CROSSLIST app and try again.",
    );
  } finally {
    submitButton.disabled = false;
    submitButton.textContent = "Find this playlist";
  }
}

form.addEventListener("submit", (event) => {
  event.preventDefault();
  loadPreview();
});

const params = new URLSearchParams(window.location.search);
const sharedUrl = params.get("url");
const sharedStorefront = params.get("storefront");
if (sharedStorefront) {
  storefrontInput.value = sharedStorefront.toLowerCase();
}
if (sharedUrl) {
  urlInput.value = sharedUrl;
  loadPreview();
}
