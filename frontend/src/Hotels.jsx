export default function Hotels({ destination }) {
  const hotels = destination.hotels ?? [];

  return (
    <section className="panel hotels-section">
      <h2>Hôtels à {destination.destination}</h2>

      <p className="hotels-intro">
        Suggestions classées selon les notes et l’analyse des avis.
        Prix et disponibilités non renseignés.
      </p>

      {hotels.length === 0 ? (
        <p>
          Aucun hôtel correspondant à cette ville dans notre catalogue.
        </p>
      ) : (
        <div className="hotels-grid">
          {hotels.map((hotel) => {
            const recherche = encodeURIComponent(
              [
                hotel.hotel_name,
                hotel.city,
                hotel.country,
              ]
                .filter(Boolean)
                .join(" ")
            );

            const sentimentDisponible =
              hotel.positive_ratio != null &&
              hotel.reviews_analyzed > 0;

            return (
              <article className="hotel-card" key={hotel.hotel_id}>
                <div className="hotel-card-top">
                  <span>
                    {hotel.stars != null
                      ? `${hotel.stars} étoiles`
                      : "Étoiles non renseignées"}
                  </span>

                  {hotel.user_rating != null && (
                    <strong>
                      {Number(hotel.user_rating).toFixed(1)} / 5
                    </strong>
                  )}
                </div>

                <h3>{hotel.hotel_name}</h3>

                <p>
                  {hotel.city}, {hotel.country}
                </p>

                {sentimentDisponible ? (
                  <p className="hotel-sentiment">
                    <strong>
                      {Math.round(hotel.positive_ratio * 100)} %
                    </strong>{" "}
                    d’avis classés positifs
                    <small>
                      Sur {hotel.reviews_analyzed} avis analysés
                    </small>
                  </p>
                ) : (
                  <p>Analyse des avis non disponible.</p>
                )}

                <a
                  className="hotel-link"
                  href={`https://www.google.com/maps/search/?api=1&query=${recherche}`}
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  Rechercher sur Google Maps ↗
                </a>
              </article>
            );
          })}
        </div>
      )}
    </section>
  );
}