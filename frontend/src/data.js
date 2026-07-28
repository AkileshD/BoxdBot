// ── Movie Quotes (expanded to ~50, shuffled at runtime) ──────────
export const QUOTES = [
  { text: "You're gonna need a bigger boat.", film: "Jaws" },
  { text: "Here's looking at you, kid.", film: "Casablanca" },
  { text: "Why so serious?", film: "The Dark Knight" },
  { text: "To infinity and beyond!", film: "Toy Story" },
  { text: "Just keep swimming.", film: "Finding Nemo" },
  { text: "I'm the king of the world!", film: "Titanic" },
  { text: "My precious.", film: "LOTR: The Two Towers" },
  { text: "You can't handle the truth!", film: "A Few Good Men" },
  { text: "I'll be back.", film: "The Terminator" },
  { text: "May the Force be with you.", film: "Star Wars" },
  { text: "Life is like a box of chocolates.", film: "Forrest Gump" },
  { text: "There's no place like home.", film: "The Wizard of Oz" },
  { text: "Say hello to my little friend!", film: "Scarface" },
  { text: "I see dead people.", film: "The Sixth Sense" },
  { text: "We accept the love we think we deserve.", film: "Perks of Being a Wallflower" },
  { text: "Carpe diem. Seize the day, boys.", film: "Dead Poets Society" },
  { text: "All those moments will be lost in time, like tears in rain.", film: "Blade Runner" },
  { text: "Get busy living, or get busy dying.", film: "The Shawshank Redemption" },
  { text: "You shall not pass!", film: "LOTR: Fellowship of the Ring" },
  { text: "I am Groot.", film: "Guardians of the Galaxy" },
  { text: "I'm going to make him an offer he can't refuse.", film: "The Godfather" },
  { text: "After all, tomorrow is another day.", film: "Gone with the Wind" },
  { text: "Frankly, my dear, I don't give a damn.", film: "Gone with the Wind" },
  { text: "Keep your friends close, but your enemies closer.", film: "The Godfather Part II" },
  { text: "The stuff that dreams are made of.", film: "The Maltese Falcon" },
  { text: "You talking to me?", film: "Taxi Driver" },
  { text: "I love the smell of napalm in the morning.", film: "Apocalypse Now" },
  { text: "It's alive! It's alive!", film: "Frankenstein" },
  { text: "What we do in life echoes in eternity.", film: "Gladiator" },
  { text: "Hope is a good thing, maybe the best of things.", film: "The Shawshank Redemption" },
  { text: "Hasta la vista, baby.", film: "Terminator 2" },
  { text: "I drink your milkshake!", film: "There Will Be Blood" },
  { text: "The first rule of Fight Club is: you do not talk about Fight Club.", film: "Fight Club" },
  { text: "To see the world, things dangerous to come to.", film: "The Secret Life of Walter Mitty" },
  { text: "Nobody puts Baby in a corner.", film: "Dirty Dancing" },
  { text: "Here's Johnny!", film: "The Shining" },
  { text: "I could've got more.", film: "Schindler's List" },
  { text: "I wish I knew how to quit you.", film: "Brokeback Mountain" },
  { text: "Not quite my tempo.", film: "Whiplash" },
  { text: "In this world, you get what you pay for.", film: "The Grand Budapest Hotel" },
  { text: "It does not do to dwell on dreams and forget to live.", film: "Harry Potter" },
  { text: "Chewie, we're home.", film: "Star Wars: The Force Awakens" },
  { text: "Adventure is out there!", film: "Up" },
  { text: "Roads? Where we're going, we don't need roads.", film: "Back to the Future" },
  { text: "I'm walking here!", film: "Midnight Cowboy" },
  { text: "You had me at hello.", film: "Jerry Maguire" },
  { text: "Do, or do not. There is no try.", film: "The Empire Strikes Back" },
  { text: "I feel the need, the need for speed.", film: "Top Gun" },
  { text: "Wax on, wax off.", film: "The Karate Kid" },
  { text: "One does not simply walk into Mordor.", film: "LOTR: Fellowship of the Ring" },
];

// Fisher-Yates shuffle
export function shuffleArray(arr) {
  const a = [...arr];
  for (let i = a.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [a[i], a[j]] = [a[j], a[i]];
  }
  return a;
}

// ── Poster URLs (TMDB w780) ────────────────────────────────
export const POSTERS = [
  "https://image.tmdb.org/t/p/w780/saHP97rTPS5eLmrLQEcANmKrsFl.jpg",  // Godfather
  "https://image.tmdb.org/t/p/w780/q6y0Go1tsGEsmtFryDOJo3dEmqu.jpg",  // Shawshank
  "https://image.tmdb.org/t/p/w780/pB8BM7pdSp6B6Ih7QZ4DrQ3PmJK.jpg",  // Schindler's List
  "https://image.tmdb.org/t/p/w780/oaGvjB0DvdhXhOAuADfHb261ZHa.jpg",  // 12 Angry Men
  "https://image.tmdb.org/t/p/w780/hek3koDUyRQk7FIhPXsa6mT2Zc3.jpg",  // Pulp Fiction
  "https://image.tmdb.org/t/p/w780/gEU2QniE6E77NI6lCU6MxlNBvIx.jpg",  // LOTR Return
  "https://image.tmdb.org/t/p/w780/3bhkrj58Vtu7enYsLeMLoSBPBan.jpg",  // LOTR FOTR
  "https://image.tmdb.org/t/p/w780/nkayOAUBUu4mMvyNf9iHSUiPjF1.jpg",  // Dark Knight
  "https://image.tmdb.org/t/p/w780/qJ2tW6WMUDux911r6m7haRef0WH.jpg",  // Fight Club
  "https://image.tmdb.org/t/p/w780/mDfJG3LC3Dqb67AZ52x3Z0jU0uB.jpg",  // Inception
  "https://image.tmdb.org/t/p/w780/f89U3ADr1oiB1s9GkdPOEpXUk5H.jpg",  // Matrix
  "https://image.tmdb.org/t/p/w780/hYFHR5PUhLRCcSUbCkMsFy5GRFG.jpg",  // Goodfellas
  "https://image.tmdb.org/t/p/w780/avedvodAZUcwqevBfm8p4G2NziQ.jpg",  // Interstellar
  "https://image.tmdb.org/t/p/w780/9xjZS2rlVxm8SFx8kPC3aIGCOYQ.jpg",  // Parasite
  "https://image.tmdb.org/t/p/w780/39wmItIWsg5sZMyRUHLkWBcuVCM.jpg",  // Casablanca
  "https://image.tmdb.org/t/p/w780/lIv1QinFqz4dlp5U4lQ6HaiskOZ.jpg",  // Spirited Away
  "https://image.tmdb.org/t/p/w780/rzdPqYx7Um4FUZeD8wpXqoSrxr.jpg",   // Forrest Gump
  "https://image.tmdb.org/t/p/w780/kdPMUMJzyYAc4roD52qavX0nLIC.jpg",  // Whiplash
  "https://image.tmdb.org/t/p/w780/gGEsBPAijhVUFoiNpgZXqRVWJt2.jpg",  // Leon
  "https://image.tmdb.org/t/p/w780/dVxRa5QFdD532y3JRu7E3sHb4LQ.jpg",  // Amadeus
  "https://image.tmdb.org/t/p/w780/2Xgb7RWx7GlLCGNIjBrMaXBSF9o.jpg",  // City of God
];

// ── Jackpot reel symbols ────────────────────────────────
export const JACKPOT_SYMBOLS = ['BB', '★', '▶', '■', 'BB', '◆', 'BB'];

// ── Watch suggestions ───────────────────────────────────
export const WATCH_SUGGESTIONS = [
  "Wait, have you seen 'The 400 Blows' yet? BoxdBot is thinking...",
  "Meanwhile, watch Stalker (1979).",
  "Meanwhile, re-watch Mulholland Drive.",
  "Meanwhile, try The Straight Story.",
  "Meanwhile, revisit Chinatown (1974).",
  "Meanwhile, start Chungking Express.",
  "Meanwhile, queue up Ikiru (1952).",
  "Meanwhile, revisit Dead Poets Society.",
  "Meanwhile, try Aftersun (2022).",
  "Have you seen Yi Yi (2000)? BoxdBot is thinking...",
  "Meanwhile, check out Still Walking (2008).",
  "Meanwhile, queue up Perfect Days (2023).",
];
