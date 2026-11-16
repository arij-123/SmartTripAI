import { useState } from "react";
import "./App.css";

const INTERETS = {
  culture: "Culture",
  nature: "Nature",
  adventure: "Aventure",
  gastronomy: "Gastronomie",
  nightlife: "Vie nocturne",
};

async function api(path, { token, body } = {}) {
  let response;

  try {
    response = await fetch(`/api${path}`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      ...(body !== undefined ? { body: JSON.stringify(body) } : {}),
    });
  } catch {
    throw new Error("Connexion impossible. Vérifie que FastAPI fonctionne.");
  }

  const data = await response.json().catch(() => null);

  if (!response.ok) {
    if (response.status === 401) {
      throw new Error(
        "Connexion refusée ou session expirée. Reconnecte-toi."
      );
    }

    const detail = data?.detail;
    const message = Array.isArray(detail)
      ? detail.map((item) => `${item.loc?.at(-1)} : ${item.msg}`).join(" — ")
      : typeof detail === "string"
        ? detail
        : `Erreur du serveur (${response.status}).`;

    throw new Error(message);
  }

  return data;
}

function Activite({ activite }) {
  const carteDisponible =
    activite.latitude != null && activite.longitude != null;

  return (
    <li className="activity">
      <div>
        <strong>{activite.nom}</strong>
        <small>
          {INTERETS[activite.interet] || activite.categorie}
        </small>
      </div>

      {carteDisponible && (
        <a
          href={`https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(
            `${activite.latitude},${activite.longitude}`
          )}`}
          target="_blank"
          rel="noreferrer"
        >
          Carte ↗
        </a>
      )}
    </li>
  );
}

export default function App() {
  // Le token reste en mémoire pour cette première démonstration.
  const [token, setToken] = useState("");
  const [mode, setMode] = useState("login");
  const [busy, setBusy] = useState(false);
  const [erreur, setErreur] = useState("");
  const [info, setInfo] = useState("");
  const [resultat, setResultat] = useState(null);
  const [selection, setSelection] = useState(0);

  const [compte, setCompte] = useState({
    first_name: "",
    last_name: "",
    email: "",
    password: "",
  });

  const [preferences, setPreferences] = useState({
    budget_total: 1500,
    jours: 5,
    mois: 6,
    climat: "chaud",
    interets: ["culture", "nature"],
  });

  function modifierCompte(event) {
    setCompte({ ...compte, [event.target.name]: event.target.value });
  }

  function modifierPreference(event) {
    setPreferences({
      ...preferences,
      [event.target.name]: event.target.value,
    });
  }

  function choisirInteret(interet) {
    setPreferences((previous) => ({
      ...previous,
      interets: previous.interets.includes(interet)
        ? previous.interets.filter((item) => item !== interet)
        : [...previous.interets, interet],
    }));
  }

  async function authentifier(event) {
    event.preventDefault();
    setBusy(true);
    setErreur("");
    setInfo("");

    try {
      if (mode === "signup") {
        await api("/auth/signup", { body: compte });
        setMode("login");
        setCompte((previous) => ({ ...previous, password: "" }));
        setInfo("Compte créé. Connecte-toi pour préparer ton voyage.");
      } else {
        const data = await api("/auth/login", {
          body: {
            email: compte.email,
            password: compte.password,
          },
        });
        setToken(data.access_token);
        setCompte((previous) => ({ ...previous, password: "" }));
      }
    } catch (error) {
      setErreur(error.message);
    } finally {
      setBusy(false);
    }
  }

  async function generer(event) {
    event.preventDefault();
    setErreur("");
    setInfo("");
    setResultat(null);

    if (!preferences.interets.length) {
      setErreur("Sélectionne au moins un centre d’intérêt.");
      return;
    }

    setBusy(true);

    try {
      const profil = await api("/profiles", {
        token,
        body: {
          ...preferences,
          budget_total: Number(preferences.budget_total),
          jours: Number(preferences.jours),
          mois: Number(preferences.mois),
        },
      });

      const data = await api(
        `/profiles/${profil.id}/recommendations?methode=weighted`,
        { token }
      );

      setResultat(data);
      setSelection(0);
    } catch (error) {
      setErreur(error.message);
    } finally {
      setBusy(false);
    }
  }

  function deconnecter() {
    setToken("");
    setResultat(null);
    setErreur("");
    setInfo("");
  }

  const destination = resultat?.destinations?.[selection];

  return (
    <div className="app">
      <header className="navbar">
        <a className="brand" href="/">
          <span className="brand-icon">S</span>
          SmartTrip<span>AI</span>
        </a>

        <div className="nav-right">
          <span>Des voyages qui vous ressemblent</span>
          {token && (
            <button
              className="secondary"
              onClick={deconnecter}
              disabled={busy}
            >
              Déconnexion
            </button>
          )}
        </div>
      </header>

      <main>
        <section className="hero">
          <div className="eyebrow">VOTRE PROCHAINE ESCAPADE</div>
          <h1>Vos envies.<br /><em>Votre prochain voyage.</em></h1>
          <p>
            Découvrez des destinations adaptées à vos préférences
            et explorez un programme d’activités jour par jour.
          </p>
          <div className="hero-tags">
            <span>Destinations personnalisées</span>
            <span>Activités à découvrir</span>
            <span>Planning quotidien</span>
          </div>
        </section>

        {erreur && <div className="alert error" role="alert">{erreur}</div>}
        {info && <div className="alert success" role="status">{info}</div>}

        {!token ? (
          <section className="panel auth-panel">
            <div className="eyebrow">BIENVENUE À BORD</div>
            <h2>{mode === "login" ? "Connectez-vous" : "Créez votre compte"}</h2>
            <p className="muted">Votre prochaine découverte commence ici.</p>

            <form onSubmit={authentifier}>
              <fieldset disabled={busy}>
                {mode === "signup" && (
                  <div className="two-columns">
                    <label>
                      Prénom
                      <input
                        name="first_name"
                        value={compte.first_name}
                        onChange={modifierCompte}
                        autoComplete="given-name"
                        maxLength={100}
                        required
                      />
                    </label>
                    <label>
                      Nom
                      <input
                        name="last_name"
                        value={compte.last_name}
                        onChange={modifierCompte}
                        autoComplete="family-name"
                        maxLength={100}
                        required
                      />
                    </label>
                  </div>
                )}

                <label>
                  Adresse e-mail
                  <input
                    name="email"
                    type="email"
                    value={compte.email}
                    onChange={modifierCompte}
                    autoComplete="email"
                    required
                  />
                </label>

                <label>
                  Mot de passe
                  <input
                    name="password"
                    type="password"
                    value={compte.password}
                    onChange={modifierCompte}
                    autoComplete={
                      mode === "signup" ? "new-password" : "current-password"
                    }
                    minLength={mode === "signup" ? 15 : 1}
                    maxLength={128}
                    required
                  />
                </label>

                {mode === "signup" && (
                  <small className="muted">Au moins 15 caractères.</small>
                )}

                <button className="primary full" type="submit">
                  {busy
                    ? "Veuillez patienter…"
                    : mode === "login"
                      ? "Se connecter →"
                      : "Créer mon compte →"}
                </button>

                <button
                  className="text-button full"
                  type="button"
                  onClick={() => {
                    setMode(mode === "login" ? "signup" : "login");
                    setErreur("");
                    setInfo("");
                  }}
                >
                  {mode === "login"
                    ? "Pas encore de compte ? S’inscrire"
                    : "Déjà inscrit ? Se connecter"}
                </button>
              </fieldset>
            </form>
          </section>
        ) : (
          <div className="workspace">
            <aside className="panel preferences">
              <div className="eyebrow">01 — VOS PRÉFÉRENCES</div>
              <h2>Imaginez votre séjour</h2>

              <form onSubmit={generer}>
                <fieldset disabled={busy}>
                  <label>
                    Budget total estimé (USD)
                    <input
                      name="budget_total"
                      type="number"
                      min="0.01"
                      max="9999999999.99"
                      step="0.01"
                      value={preferences.budget_total}
                      onChange={modifierPreference}
                      required
                    />
                  </label>

                  <div className="two-columns">
                    <label>
                      Durée en jours
                      <input
                        name="jours"
                        type="number"
                        min="1"
                        max="365"
                        value={preferences.jours}
                        onChange={modifierPreference}
                        required
                      />
                    </label>

                    <label>
                      Mois du voyage
                      <select
                        name="mois"
                        value={preferences.mois}
                        onChange={modifierPreference}
                      >
                        {[
                          "Janvier", "Février", "Mars", "Avril",
                          "Mai", "Juin", "Juillet", "Août",
                          "Septembre", "Octobre", "Novembre", "Décembre",
                        ].map((mois, index) => (
                          <option key={mois} value={index + 1}>{mois}</option>
                        ))}
                      </select>
                    </label>
                  </div>

                  <label>
                    Climat préféré
                    <select
                      name="climat"
                      value={preferences.climat}
                      onChange={modifierPreference}
                    >
                      <option value="chaud">Chaud</option>
                      <option value="doux">Doux</option>
                      <option value="froid">Froid</option>
                    </select>
                  </label>

                  <p className="label">Qu’aimez-vous découvrir ?</p>
                  <div className="interests">
                    {Object.entries(INTERETS).map(([value, label]) => (
                      <button
                        key={value}
                        type="button"
                        className={
                          preferences.interets.includes(value)
                            ? "chip active"
                            : "chip"
                        }
                        aria-pressed={preferences.interets.includes(value)}
                        onClick={() => choisirInteret(value)}
                      >
                        {label}
                      </button>
                    ))}
                  </div>

                  <button className="primary full" type="submit">
                    {busy ? "Préparation de votre voyage…" : "Trouver mon voyage →"}
                  </button>
                </fieldset>
              </form>
            </aside>

            <section className="results" aria-live="polite">
              {!resultat ? (
                <div className="panel empty">
                  <div className="compass">✦</div>
                  <h2>
                    {busy ? "Votre voyage prend forme…" : "Le monde vous attend"}
                  </h2>
                  <p>
                    {busy
                      ? "Nous recherchons les destinations et leurs activités."
                      : "Renseignez vos envies pour découvrir vos suggestions."}
                  </p>
                </div>
              ) : resultat.destinations.length === 0 ? (
                <div className="panel empty">
                  <h2>Aucune destination trouvée</h2>
                  <p>Essayez un autre budget, un autre mois ou un autre climat.</p>
                </div>
              ) : (
                <>
                  <div className="results-heading">
                    <div className="eyebrow">02 — VOS INSPIRATIONS</div>
                    <h2>{resultat.destinations.length} destinations à explorer</h2>
                  </div>

                  <div className="destination-grid">
                    {resultat.destinations.map((item, index) => (
                      <button
                        key={`${item.pays}-${item.destination}`}
                        className={`destination-card ${
                          selection === index ? "selected" : ""
                        }`}
                        onClick={() => setSelection(index)}
                        aria-pressed={selection === index}
                      >
                        <span className="rank">CHOIX {index + 1}</span>
                        <h3>{item.destination}</h3>
                        <span>{item.pays}</span>
                        <div className="price">
                          {Number(item.budget_estime_par_jour_usd).toFixed(0)}
                          {" USD "}
                          <small>/ jour estimé</small>
                        </div>
                      </button>
                    ))}
                  </div>

                  {destination && (
                    <div className="panel itinerary">
                      <div className="eyebrow">03 — VOTRE PROGRAMME</div>
                      <h2>À la découverte de {destination.destination}</h2>
                      <p className="muted">
                        Suggestions à adapter à votre rythme. Vérifiez les
                        horaires, les tarifs et les trajets avant vos visites.
                      </p>

                      {destination.avertissements?.map((message) => (
                        <div className="notice" key={message}>{message}</div>
                      ))}

                      {destination.planning.map((jour) => (
                        <article className="day" key={jour.jour}>
                          <h3><span>{jour.jour}</span> Jour {jour.jour}</h3>
                          <div className="two-columns day-columns">
                            <div>
                              <h4>En journée</h4>
                              <ul>
                                {jour.activites_jour.map((activite, index) => (
                                  <Activite key={index} activite={activite} />
                                ))}
                              </ul>
                              {!jour.activites_jour.length && (
                                <p className="muted">Aucune activité disponible.</p>
                              )}
                            </div>
                            <div>
                              <h4>Suggestion de soirée</h4>
                              <ul>
                                {jour.activites_soir.map((activite, index) => (
                                  <Activite key={index} activite={activite} />
                                ))}
                              </ul>
                              {!jour.activites_soir.length && (
                                <p className="muted">Soirée libre.</p>
                              )}
                            </div>
                          </div>
                        </article>
                      ))}
                    </div>
                  )}
                </>
              )}
            </section>
          </div>
        )}
      </main>

      <footer>SmartTripAI · Explorer selon vos envies</footer>
    </div>
  );
}