import React from 'react';
import { useNavigate } from 'react-router-dom';

interface HeaderProps {
  currentStep?: number;
  sessionId?: string;
}

export const Header: React.FC<HeaderProps> = ({ currentStep, sessionId }) => {
  const navigate = useNavigate();

  const steps = [
    { num: 1, name: 'Details', path: sessionId ? `/session/${sessionId}/details` : '/' },
    { num: 2, name: 'Upload', path: sessionId ? `/session/${sessionId}/upload` : '/' },
    { num: 3, name: 'Analyze', path: sessionId ? `/session/${sessionId}/analyze` : '/' },
    { num: 4, name: 'Review', path: sessionId ? `/session/${sessionId}/review` : '/' },
    { num: 5, name: 'Generate', path: sessionId ? `/session/${sessionId}/result` : '/' },
  ];

  return (
    <header className="app-header">
      <div className="brand-title" onClick={() => navigate('/')}>
        <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ color: '#38bdf8' }}>
          <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
          <path d="m9 12 2 2 4-4" />
        </svg>
        <span>CTC PM Generator</span>
      </div>

      {currentStep && (
        <div className="stepper">
          {steps.map((s) => {
            const isCompleted = currentStep > s.num;
            const isActive = currentStep === s.num;
            return (
              <div
                key={s.num}
                className={`step-item ${isActive ? 'active' : ''} ${isCompleted ? 'completed' : ''}`}
                style={{ cursor: isCompleted ? 'pointer' : 'default' }}
                onClick={() => {
                  if (isCompleted && sessionId) {
                    navigate(s.path);
                  }
                }}
              >
                <span>{isCompleted ? '✓' : s.num}.</span>
                <span>{s.name}</span>
              </div>
            );
          })}
        </div>
      )}
    </header>
  );
};
