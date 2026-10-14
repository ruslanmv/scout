/* global React, ReactDOM */
/* Scout landing entry — hero + scanning animation, then a real navigation to
   the dedicated report page (multi-page product; the report and its sections
   are separate routes under report/). */
const { useState: uS, useEffect: uE, useRef: uR } = React;
const SA = window.SCOUT;
const UI = window.ScoutUI;
const Landing = window.ScoutLanding;

const SCAN_LINES = [
  "Reading developer signals…",
  "GitHub · Hugging Face",
  "Jobs · news · community",
  "Matching to your goal",
  "Building your report"
];

function ToolHeader() {
  return (
    <header className="tool-header">
      <div className="tool-header__in">
        <a className="tool-header__back" href="./">← <span>Home</span></a>
        <div className="tool-header__title"><span className="gl">◇</span> Scout</div>
        <div className="tool-header__user"><span className="live"><span className="dot" />LIVE</span><span className="avatar">RM</span></div>
      </div>
    </header>
  );
}

function reportUrl(profile, city, country, goal) {
  const q = new URLSearchParams({ profile, city, country, goal });
  return "report/?" + q.toString();
}

function scoutEvent(name) {
  if (Array.isArray(window.dataLayer)) window.dataLayer.push({ event: "scout_" + name, source: "landing" });
  try { window.dispatchEvent(new CustomEvent("scout:analytics", { detail: { event: "scout_" + name, source: "landing" } })); } catch (_) {}
}

function App() {
  const [phase, setPhase] = uS("hero");
  const query = new URLSearchParams(window.location.search);
  const [country, setCountry] = uS(() => query.get("country") || "Italy");
  const [city, setCity] = uS(() => query.get("city") || "Rome");
  const [goal, setGoal] = uS(() =>
    SA.GOALS.some(g => g.id === query.get("goal")) ? query.get("goal") : "build_portfolio");
  // No fabricated default: only auto-select the highest observed local role,
  // or preserve an explicit user-entered/deep-linked profession.
  const [profile, setProfile] = uS(() => (query.get("profile") || "").trim());
  const userSelectedRole = uR(Boolean((query.get("profile") || "").trim()));
  const [pulse, setPulse] = uS(null);
  const [pulseStatus, setPulseStatus] = uS("loading");
  uE(() => {
    const controller = new AbortController();
    fetch("data/pulse/latest.json", {cache: "no-store", signal: controller.signal})
      .then(response => {
        if (!response.ok) throw new Error("Current Pulse unavailable");
        return response.json();
      })
      .then(feed => {
        if (!feed || feed.schema_version !== 1) throw new Error("Unsupported Pulse feed");
        setPulse(feed);
        setPulseStatus("ready");
      })
      .catch(error => { if (!controller.signal.aborted) setPulseStatus("error"); });
    return () => controller.abort();
  }, []);
  uE(() => {
    if (userSelectedRole.current || !pulse) return;
    const observed = window.ScoutRanking.roles(pulse, city, country);
    setProfile(observed ? observed.items[0].name : "");
  }, [pulse, city, country]);
  const selectProfession = value => {
    userSelectedRole.current = true;
    setProfile(value);
  };
  const [scanIdx, setScanIdx] = uS(0);
  const [animSafe, setAnimSafe] = uS(false);

  uE(() => { setAnimSafe(false); const t = setTimeout(() => setAnimSafe(true), 1700); return () => clearTimeout(t); }, [phase]);

  const goalObj = SA.GOALS.find(g => g.id === goal) || SA.GOALS[0];

  function generate() { if (!profile.trim()) return; scoutEvent("plan_cta_clicked"); setPhase("scanning"); setScanIdx(0); window.scrollTo({ top: 0, behavior: "smooth" }); }

  // Advance the scanning log, then navigate to the real report route.
  uE(() => {
    if (phase !== "scanning") return;
    if (scanIdx >= SCAN_LINES.length) {
      const t = setTimeout(() => { scoutEvent("report_navigation_started"); window.location.href = reportUrl(profile, city, country, goal); }, 420);
      return () => clearTimeout(t);
    }
    const t = setTimeout(() => setScanIdx(i => i + 1), scanIdx === 0 ? 360 : 300);
    return () => clearTimeout(t);
  }, [phase, scanIdx, profile, city, country, goal]);

  return (
    <div className={"app" + (animSafe ? " anim-safe" : "")}>
      {phase === "hero" && (
        <Landing
          profile={profile} setProfile={selectProfession}
          city={city} country={country}
          setLocation={(c, co) => { setCity(c); setCountry(co); }}
          goal={goal} setGoal={setGoal}
          onGenerate={generate}
          pulse={pulse} pulseStatus={pulseStatus}
        />
      )}

      {phase === "scanning" && (
        <React.Fragment>
          <ToolHeader />
          <div className="wrap">
            <section className="darkpanel scout-hero">
              <UI.Constellation />
              <div style={{ position: "relative" }}>
                <div className="eyebrow"><span className="dot" />Your next move</div>
                <h1>Building <span className="em">your plan</span>…</h1>
                <div className="scanning">
                  <div className="scan-ring"><UI.ScoreRing value={Math.min(100, Math.round((scanIdx / SCAN_LINES.length) * 100))} size={92} stroke={6} dark={true} /></div>
                  <div className="scan-log">{SCAN_LINES[Math.min(scanIdx, SCAN_LINES.length - 1)]}</div>
                  <div className="scan-sub">{city}, {country} · {goalObj.label} · {profile}</div>
                </div>
              </div>
            </section>
          </div>
        </React.Fragment>
      )}
    </div>
  );
}

ReactDOM.createRoot(document.getElementById("root")).render(<App />);
