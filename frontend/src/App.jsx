import { useState } from 'react';
import { LandingScreen } from './components/LandingScreen';
import { UploadScreen } from './components/UploadScreen';
import { AgentScreen } from './components/AgentScreen';
import './App.css';

function App() {
  const [screen, setScreen] = useState('landing'); // landing | upload | agent
  const [sessionId, setSessionId] = useState(null);
  const [filesProcessed, setFilesProcessed] = useState(0);

  const handleGetStarted = () => {
    setScreen('upload');
  };

  const handleUploadComplete = (id, count) => {
    setSessionId(id);
    setFilesProcessed(count);
    setScreen('agent');
  };

  const handleBackToLanding = () => {
    setSessionId(null);
    setFilesProcessed(0);
    setScreen('landing');
  };

  const handleEndSession = () => {
    fetch(`http://localhost:8001/sessions/${sessionId}`, {
      method: 'DELETE'
    }).catch(console.error);
    
    handleBackToLanding();
  };

  return (
    <div className="app">
      {screen === 'landing' && (
        <LandingScreen onGetStarted={handleGetStarted} />
      )}
      
      {screen === 'upload' && (
        <UploadScreen 
          onUploadComplete={handleUploadComplete}
          onBack={handleBackToLanding}
        />
      )}
      
      {screen === 'agent' && sessionId && (
        <AgentScreen 
          sessionId={sessionId}
          filesProcessed={filesProcessed}
          onEndSession={handleEndSession}
        />
      )}
    </div>
  );
}

export default App;
