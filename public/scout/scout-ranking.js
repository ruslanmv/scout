/* Shared evidence gate for Scout landing and Pulse. No synthetic rankings. */
(function () {
  "use strict";
  // Accept at most one weekly collection window. The source collected_at
  // must also be within this window; a new feed cannot revive old evidence.
  const MAX_AGE_MS = 8 * 24 * 60 * 60 * 1000;
  const CLOCK_SKEW_MS = 60 * 60 * 1000;

  function isRecent(timestamp, now) {
    if (typeof timestamp !== "string") return false;
    const value = Date.parse(timestamp);
    const age = now - value;
    return Number.isFinite(value) && age >= -CLOCK_SKEW_MS && age <= MAX_AGE_MS;
  }

  function freshFeed(feed, now) {
    return Boolean(feed && feed.schema_version === 1 &&
      isRecent(feed.generated_at, now));
  }

  function roles(feed, city, country, now = Date.now()) {
    if (!freshFeed(feed, now) || !feed.regions) return null;
    for (const region of [...new Set([city, country])]) {
      if (!region || region === "Worldwide") continue;
      const result = feed.regions[region];
      if (!result || result.status !== "measured" || !Array.isArray(result.items)) continue;
      const byName = new Map();
      for (const item of result.items) {
        if (!item || typeof item.name !== "string" || !item.name.trim()) continue;
        // Source attribution and the *actual collection time* are required.
        // Rebuilding today's feed with yesterday's signal must not renew it.
        if (typeof item.source !== "string" ||
            !item.source.trim() ||
            ["curated", "unknown", "demo", "sample"].includes(item.source.toLowerCase()) ||
            !isRecent(item.collected_at, now)) continue;
        const count = Number(item.sample_size);
        if (!Number.isFinite(count) || count <= 0) continue;
        const name = item.name.trim(), key = name.toLowerCase();
        const old = byName.get(key);
        if (!old || Number(old.sample_size) < count) {
          byName.set(key, { name, sample_size: count,
            source: item.source, collected_at: item.collected_at });
        }
      }
      const ranked = [...byName.values()].sort((a, b) =>
        b.sample_size - a.sample_size || a.name.localeCompare(b.name));
      if (ranked.length >= 5) {
        return {items: ranked.slice(0, 5), region, date: feed.date,
          generated_at: feed.generated_at};
      }
    }
    // Never borrow another region or the worldwide curated fallback.
    return null;
  }

  function skills(feed, city, country, now = Date.now()) {
    if (!freshFeed(feed, now)) return [];
    const key = (country + ":" + city).toLowerCase();
    const byRegion = feed.skills_by_region || {};
    const input = byRegion[key] || byRegion[country.toLowerCase()] || feed.skills || [];
    if (!Array.isArray(input)) return [];
    return input.filter(x => x && typeof x.name === "string" && x.name.trim() &&
      x.source === "topic_proxy" && Number.isFinite(Number(x.score)))
      .sort((a, b) => Number(b.score) - Number(a.score) || a.name.localeCompare(b.name))
      .slice(0, 5);
  }

  window.ScoutRanking = { roles, skills, freshFeed, isRecent };
})();
