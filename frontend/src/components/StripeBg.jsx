import { useState, useEffect } from 'react';
import { POSTERS } from '../data.js';

/*
  7 diagonal poster stripes. This is the PERMANENT background on BOTH pages.
  Uses a single skewed container so there are never gaps at the edges.
  Each stripe independently cycles its poster on a staggered wave timer.
*/

function Stripe({ index }) {
  const [posterIdx, setPosterIdx] = useState(
    (index * 3) % POSTERS.length // deterministic initial spread
  );

  useEffect(() => {
    // Stagger: each stripe waits index * 700ms before starting its cycle
    const delay = index * 700;
    let intervalId;
    const timeout = setTimeout(() => {
      intervalId = setInterval(() => {
        setPosterIdx(prev => (prev + 1) % POSTERS.length);
      }, 5000); // change every 5s
    }, delay);
    return () => {
      clearTimeout(timeout);
      clearInterval(intervalId);
    };
  }, [index]);

  return (
    <div
      className="stripe"
      style={{ backgroundImage: `url(${POSTERS[posterIdx]})` }}
    />
  );
}

export default function StripeBg() {
  return (
    <div className="stripe-container">
      {Array.from({ length: 7 }).map((_, i) => (
        <Stripe key={i} index={i} />
      ))}
    </div>
  );
}
