import { useState } from 'react';
import Setup from './pages/Setup.jsx';
import Chat from './pages/Chat.jsx';

export default function App() {
  const [session, setSession] = useState(null); // null = not started

  function handleSessionStart(apiKey, pastFindings) {
    setSession({ apiKey, pastFindings });
  }

  function handleEndSession() {
    setSession(null);
  }

  if (!session) {
    return <Setup onSessionStart={handleSessionStart} />;
  }

  return (
    <Chat
      apiKey={session.apiKey}
      pastFindings={session.pastFindings}
      onEndSession={handleEndSession}
    />
  );
}
