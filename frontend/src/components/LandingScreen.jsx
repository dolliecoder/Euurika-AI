import { useState } from 'react';
import styles from './LandingScreen.module.css';

export function LandingScreen({ onGetStarted }) {
  const [showDemo, setShowDemo] = useState(false);

  return (
    <div className={styles.container}>
      {/* Animated background */}
      <div className={styles.bgGradient} />
      <div className={styles.bgGlow} />
      
      {/* Navigation */}
      <nav className={styles.nav}>
        <div className={styles.logo}>
          <EurikaLogo />
          <span>Eurika AI</span>
        </div>
        <button className={styles.navButton} onClick={onGetStarted}>
          Get Started
        </button>
      </nav>

      {/* Hero Section */}
      <section className={styles.hero}>
        <div className={styles.badge}>
          <span className={styles.badgeDot} />
          Voice-Powered FAQ Agent
        </div>
        
        <h1 className={styles.title}>
          Your Documents,<br />
          <span className={styles.titleAccent}>Voice-Activated</span>
        </h1>
        
        <p className={styles.subtitle}>
          Upload your FAQ documents and talk to them naturally. 
          Eurika understands context, speaks naturally, and never makes you read.
        </p>

        <div className={styles.cta}>
          <button className={styles.primaryBtn} onClick={onGetStarted}>
            <MicIcon />
            Start Talking
          </button>
          <button 
            className={styles.secondaryBtn}
            onClick={() => setShowDemo(!showDemo)}
          >
            {showDemo ? 'Hide Demo' : 'Watch Demo'}
          </button>
        </div>

        {/* Feature Pills */}
        <div className={styles.features}>
          <FeaturePill icon={<BrainIcon />} text="GPT-4 Powered" />
          <FeaturePill icon={<ZapIcon />} text="Real-time Streaming" />
          <FeaturePill icon={<ShieldIcon />} text="Private & Secure" />
          <FeaturePill icon={<WaveIcon />} text="Voice Interface" />
        </div>
      </section>

      {/* Demo Section */}
      {showDemo && (
        <section className={styles.demo}>
          <div className={styles.demoCard}>
            <div className={styles.demoVisual}>
              <div className={styles.waveContainer}>
                {[...Array(20)].map((_, i) => (
                  <div 
                    key={i} 
                    className={styles.waveBar}
                    style={{ 
                      animationDelay: `${i * 0.05}s`,
                      height: `${20 + Math.random() * 40}px`
                    }}
                  />
                ))}
              </div>
              <div className={styles.demoMic}>
                <MicIcon />
              </div>
            </div>
            <div className={styles.demoText}>
              <p>"What is your refund policy?"</p>
            </div>
          </div>
        </section>
      )}

      {/* How It Works */}
      <section className={styles.howItWorks}>
        <h2>How It Works</h2>
        <div className={styles.steps}>
          <StepCard 
            number="01"
            title="Upload Documents"
            description="Drop your PDF, Markdown, or text files. Eurika reads and understands them all."
            icon={<UploadIcon />}
          />
          <StepCard 
            number="02"
            title="Start Speaking"
            description="Just talk naturally. No buttons, no menus. Eurika listens and understands."
            icon={<MicIcon />}
          />
          <StepCard 
            number="03"
            title="Get Answers"
            description="Hear the answer instantly. Streaming audio, conversational responses."
            icon={<PlayIcon />}
          />
        </div>
      </section>

      {/* Footer */}
      <footer className={styles.footer}>
        <p>Built with FastAPI, ChromaDB, OpenAI & ElevenLabs</p>
      </footer>
    </div>
  );
}

function FeaturePill({ icon, text }) {
  return (
    <div className={styles.pill}>
      {icon}
      <span>{text}</span>
    </div>
  );
}

function StepCard({ number, title, description, icon }) {
  return (
    <div className={styles.stepCard}>
      <div className={styles.stepIcon}>{icon}</div>
      <div className={styles.stepNumber}>{number}</div>
      <h3>{title}</h3>
      <p>{description}</p>
    </div>
  );
}

// SVG Icons
export function EurikaLogo() {
  return (
    <svg width="32" height="32" viewBox="0 0 32 32" fill="none">
      <defs>
        <linearGradient id="logoGrad" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" stopColor="#8b5cf6" />
          <stop offset="100%" stopColor="#06b6d4" />
        </linearGradient>
      </defs>
      <circle cx="16" cy="16" r="14" stroke="url(#logoGrad)" strokeWidth="2" fill="none" />
      <path 
        d="M10 16 L16 10 L22 16 M16 10 L16 24" 
        stroke="url(#logoGrad)" 
        strokeWidth="2.5" 
        strokeLinecap="round"
        strokeLinejoin="round"
        fill="none"
      />
    </svg>
  );
}

export function MicIcon() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z" />
      <path d="M19 10v2a7 7 0 0 1-14 0v-2" />
      <line x1="12" y1="19" x2="12" y2="23" />
      <line x1="8" y1="23" x2="16" y2="23" />
    </svg>
  );
}

export function BrainIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M9.5 2A2.5 2.5 0 0 1 12 4.5v15a2.5 2.5 0 0 1-4.96.44 2.5 2.5 0 0 1-2.96-3.08 3 3 0 0 1-.34-5.58 2.5 2.5 0 0 1 1.32-4.24 2.5 2.5 0 0 1 1.98-3A2.5 2.5 0 0 1 9.5 2Z" />
      <path d="M14.5 2A2.5 2.5 0 0 0 12 4.5v15a2.5 2.5 0 0 0 4.96.44 2.5 2.5 0 0 0 2.96-3.08 3 3 0 0 0 .34-5.58 2.5 2.5 0 0 0-1.32-4.24 2.5 2.5 0 0 0-1.98-3A2.5 2.5 0 0 0 14.5 2Z" />
    </svg>
  );
}

export function ZapIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2" />
    </svg>
  );
}

export function ShieldIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
    </svg>
  );
}

export function WaveIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M2 12h2 M6 8v8 M10 5v14 M14 8v8 M18 6v12 M22 12h2" />
    </svg>
  );
}

export function UploadIcon() {
  return (
    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
      <polyline points="17 8 12 3 7 8" />
      <line x1="12" y1="3" x2="12" y2="15" />
    </svg>
  );
}

export function PlayIcon() {
  return (
    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <polygon points="5 3 19 12 5 21 5 3" />
    </svg>
  );
}
