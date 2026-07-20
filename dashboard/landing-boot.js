/* global React, ReactDOM, ScoutLanding */
(function () {
  const params = new URLSearchParams(window.location.search);
  const goals = window.SCOUT.GOALS;
  const profiles = window.SCOUT.PROFILES;
  const [defaultCity, defaultCountry] = (params.get('city') && params.get('country'))
    ? [params.get('city'), params.get('country')]
    : ['Rome', 'Italy'];

  function slugProfile(label) {
    return String(label || 'Developer').toLowerCase().replace(/\s+/g, '_');
  }

  function LandingShell() {
    const [profile, setProfile] = React.useState(params.get('profile') || profiles[0]);
    const [city, setCity] = React.useState(defaultCity);
    const [country, setCountry] = React.useState(defaultCountry);
    const [goal, setGoal] = React.useState(params.get('goal') || goals[0].id);
    const setLocation = (nextCity, nextCountry) => { setCity(nextCity); setCountry(nextCountry); };
    const onGenerate = () => {
      const q = new URLSearchParams({ city, country, profile: slugProfile(profile), goal, limit: '10' });
      window.location.href = `report/overview/?${q.toString()}`;
    };
    return React.createElement(ScoutLanding, { profile, setProfile, city, country, setLocation, goal, setGoal, onGenerate });
  }

  ReactDOM.createRoot(document.getElementById('root')).render(React.createElement(LandingShell));
}());
