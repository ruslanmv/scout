/* global React, ReactDOM */
/* Scout landing entry — hero + scanning animation, then a real navigation to
   the dedicated report page (multi-page product; the report and its sections
   are separate routes under report/). */
const { useState: uS, useEffect: uE } = React;
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

function App() {
  const [phase, setPhase] = uS("hero");
  const [country, setCountry] = uS("Italy");
  const [city, setCity] = uS("Rome");
  const [goal, setGoal] = uS("build_portfolio");
  const [profile, setProfile] = uS("Developer");
  const [scanIdx, setScanIdx] = uS(0);
  const [animSafe, setAnimSafe] = uS(false);

  uE(() => { setAnimSafe(false); const t = setTimeout(() => setAnimSafe(true), 1700); return () => clearTimeout(t); }, [phase]);

  const goalObj = SA.GOALS.find(g => g.id === goal) || SA.GOALS[0];

  function generate() { setPhase("scanning"); setScanIdx(0); window.scrollTo({ top: 0, behavior: "smooth" }); }

  // Advance the scanning log, then navigate to the real report route.
  uE(() => {
    if (phase !== "scanning") return;
    if (scanIdx >= SCAN_LINES.length) {
      const t = setTimeout(() => { window.location.href = reportUrl(profile, city, country, goal); }, 420);
      return () => clearTimeout(t);
    }
    const t = setTimeout(() => setScanIdx(i => i + 1), scanIdx === 0 ? 360 : 300);
    return () => clearTimeout(t);
  }, [phase, scanIdx, profile, city, country, goal]);

  return (
    <div className={"app" + (animSafe ? " anim-safe" : "")}>
      {phase === "hero" && (
        <Landing
          profile={profile} setProfile={setProfile}
          city={city} country={country}
          setLocation={(c, co) => { setCity(c); setCountry(co); }}
          goal={goal} setGoal={setGoal}
          onGenerate={generate}
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
