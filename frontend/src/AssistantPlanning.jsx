import { useEffect, useRef, useState } from "react";
import "./AssistantPlanning.css";

function ContenuChat({ api, destination, resultat, token }) {
  const planning = destination.planning ?? [];
  const [jour, setJour] = useState(planning[0]?.jour);
  const [question, setQuestion] = useState("");
  const [messages, setMessages] = useState([]);
  const [enCours, setEnCours] = useState(false);
  const fil = useRef(null);

  useEffect(() => {
    if (fil.current) {
      fil.current.scrollTop = fil.current.scrollHeight;
    }
  }, [messages, enCours, jour]);

  async function envoyer(event) {
    event.preventDefault();

    const texte = question.trim();
    if (!texte || enCours) return;

    setEnCours(true);
    setQuestion("");
    setMessages((anciens) => [
      ...anciens,
      { jour, auteur: "Vous", texte },
    ]);

    try {
      const methode = resultat.methode ?? "weighted";

      // FastAPI reçoit le pays même si la question dit seulement « ce pays ».
      const data = await api(
        `/profiles/${resultat.profile_id}/assistant?methode=${encodeURIComponent(methode)}`,
        {
          token,
          body: {
            destination: destination.destination,
            pays: destination.pays,
            jour,
            question: texte,
          },
        }
      );

      setMessages((anciens) => [
        ...anciens,
        {
          jour,
          auteur: "SmartTripAI",
          texte: data.reponse,
          sources: data.sources ?? [],
        },
      ]);
    } catch (error) {
      setMessages((anciens) => [
        ...anciens,
        {
          jour,
          auteur: "SmartTripAI",
          texte: error.message || "La réponse n’a pas pu être chargée.",
        },
      ]);
      setQuestion(texte);
    } finally {
      setEnCours(false);
    }
  }

  const visibles = messages.filter((message) => message.jour === jour);

  return (
    <section className="trip-chat" aria-label="Assistant de voyage">
      <header className="trip-chat-head">
        <div>
          <h2>Assistant de voyage</h2>
          <p>
            {destination.destination} · {destination.pays}
          </p>
        </div>

        <select
          aria-label="Journée du planning"
          value={jour}
          disabled={enCours}
          onChange={(event) => {
            setJour(Number(event.target.value));
            setQuestion("");
          }}
        >
          {planning.map((item) => (
            <option key={item.jour} value={item.jour}>
              Jour {item.jour}
            </option>
          ))}
        </select>
      </header>

      <div className="trip-chat-log" role="log" ref={fil}>
        {visibles.length === 0 && (
          <p>
            Que souhaitez-vous découvrir sur {destination.destination} ?
            Vous pouvez me poser une question sur le pays, son patrimoine
            ou votre programme du jour {jour}.
          </p>
        )}

        {visibles.map((message, index) => (
          <div
            key={index}
            className={
              message.auteur === "Vous"
                ? "trip-message trip-message-user"
                : "trip-message"
            }
          >
            <small>{message.auteur}</small>
            <p>{message.texte}</p>

            {message.sources?.length > 0 && (
              <small>
                Fiches consultées ·{" "}
                {message.sources.map((source) => source.lieu).join(", ")}
              </small>
            )}
          </div>
        ))}

        {enCours && <p>Recherche dans les fiches et le planning…</p>}
      </div>

      <form className="trip-chat-form" onSubmit={envoyer}>
        <input
          aria-label="Votre question"
          placeholder="Parle-moi de ce pays…"
          maxLength={800}
          value={question}
          disabled={enCours}
          onChange={(event) => setQuestion(event.target.value)}
        />

        <button
          type="submit"
          className="primary"
          disabled={enCours || !question.trim()}
        >
          Envoyer
        </button>
      </form>
    </section>
  );
}

export default function AssistantPlanning(props) {
  const [ouvert, setOuvert] = useState(false);
  const panneau = useRef(null);
  const bouton = useRef(null);

  useEffect(() => {
    if (ouvert) {
      panneau.current?.querySelector("input")?.focus();
    }
  }, [ouvert]);

  function fermer() {
    setOuvert(false);
    bouton.current?.focus();
  }

  if (!props.destination?.planning?.length) return null;

  return (
    <div
      className="chat-flottant"
      onKeyDown={(event) => {
        if (event.key === "Escape" && ouvert) fermer();
      }}
    >
      <div id="chat-voyage" ref={panneau} hidden={!ouvert}>
        <ContenuChat {...props} />
      </div>

      <button
        type="button"
        className="chat-bulle"
        ref={bouton}
        aria-controls="chat-voyage"
        aria-expanded={ouvert}
        aria-label={ouvert ? "Fermer le chat" : "Ouvrir le chat"}
        onClick={() => (ouvert ? fermer() : setOuvert(true))}
      >
        {ouvert ? "×" : "💬"}
      </button>
    </div>
  );
}