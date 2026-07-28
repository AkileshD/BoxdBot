import { useMemo } from 'react';
import { QUOTES, shuffleArray } from '../data.js';

export default function Footer() {
  // Shuffle once on mount, then double for infinite loop
  const shuffled = useMemo(() => {
    const s = shuffleArray(QUOTES);
    return [...s, ...s];
  }, []);

  return (
    <div className="quote-footer">
      <div className="quote-track">
        {shuffled.map((q, i) => (
          <span className="quote-item" key={i}>
            "{q.text}"
            <span className="quote-film">{q.film}</span>
          </span>
        ))}
      </div>
    </div>
  );
}
