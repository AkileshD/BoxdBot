import { useEffect, useRef, useState } from 'react';
import { JACKPOT_SYMBOLS } from '../data.js';

/*
  Real slot-machine reel. A vertical strip of symbols inside an overflow:hidden
  window. When spinning, the strip scrolls upward via translateY with a fast
  step animation so you genuinely see symbols cycling through.
*/

const FRAME_H = 72; // px height of each symbol frame

export default function Jackpot({ spinning }) {
  const [offset, setOffset] = useState(0);
  const timer = useRef(null);

  useEffect(() => {
    if (spinning) {
      timer.current = setInterval(() => {
        setOffset(prev => {
          const next = prev + 1;
          return next >= JACKPOT_SYMBOLS.length ? 0 : next;
        });
      }, 100); // fast cycle
    } else {
      clearInterval(timer.current);
      setOffset(0); // rest on first "BB"
    }
    return () => clearInterval(timer.current);
  }, [spinning]);

  return (
    <div className="jackpot-col">
      <div className="jackpot-window">
        <div
          className="jackpot-reel"
          style={{
            transform: `translateY(-${offset * FRAME_H}px)`,
            transition: spinning ? 'none' : 'transform 0.3s ease-out',
          }}
        >
          {JACKPOT_SYMBOLS.map((sym, i) => (
            <div
              key={i}
              className={`jackpot-frame${i % 2 === 0 ? ' accent' : ''}`}
            >
              {sym}
            </div>
          ))}
        </div>
      </div>
      <div className="jackpot-label">BoxdBot</div>
      <div className="jackpot-status">
        {spinning ? '● THINKING' : '○ READY'}
      </div>
    </div>
  );
}
