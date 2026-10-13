import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { createSession } from '../api/client';
import { Header } from '../components/Header';

export const HomePage: React.FC = () => {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);

  const handleNewReport = async () => {
    setLoading(true);
    try {
      const session = await createSession();
      navigate(`/session/${session.id}/details`);
    } catch (error) {
      console.error(error);
      alert('Failed to start new PM report session.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="app-container">
      <Header />
      
      <div style={{ textAlign: 'center', padding: '3rem 1rem 4rem 1rem' }}>
        <div style={{ display: 'inline-block', padding: '0.35rem 1rem', background: 'rgba(56, 189, 248, 0.1)', border: '1px solid rgba(56, 189, 248, 0.3)', borderRadius: '9999px', fontSize: '0.85rem', color: '#38bdf8', marginBottom: '1.5rem', fontWeight: 600 }}>
          Deterministic FortiGate PM Automation
        </div>
        <h1 style={{ fontSize: '3rem', fontWeight: 800, marginBottom: '1.25rem', letterSpacing: '-0.03em', lineHeight: 1.15 }}>
          Automate FortiGate <br />
          <span style={{ background: 'linear-gradient(135deg, #38bdf8 0%, #818cf8 100%)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>
            Preventive Maintenance Reports
          </span>
        </h1>
        <p style={{ maxWidth: '640px', margin: '0 auto 2.5rem auto', color: 'var(--text-muted)', fontSize: '1.1rem' }}>
          Upload screenshots in bulk. The engine OCRs, classifies all 16 appendices, extracts telemetry, applies deterministic PM rules, and injects evidence directly into your pristine template.
        </p>

        <button 
          className="btn btn-primary"
          onClick={handleNewReport}
          disabled={loading}
          style={{ padding: '0.9rem 2.2rem', fontSize: '1.1rem' }}
        >
          {loading ? 'Initializing Session...' : '+ New PM Report'}
        </button>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '1.5rem', marginTop: '1rem' }}>
        <div className="glass-card">
          <div style={{ fontSize: '1.5rem', marginBottom: '0.75rem' }}>🎯</div>
          <h3 style={{ fontSize: '1.1rem', marginBottom: '0.5rem', color: 'var(--text-main)' }}>16-Appendix Classifier</h3>
          <p style={{ fontSize: '0.9rem', color: 'var(--text-muted)' }}>
            Deterministic anchor profiles automatically detect and route screenshots to the exact appendix slots without manual tagging.
          </p>
        </div>

        <div className="glass-card">
          <div style={{ fontSize: '1.5rem', marginBottom: '0.75rem' }}>🔒</div>
          <h3 style={{ fontSize: '1.1rem', marginBottom: '0.5rem', color: 'var(--text-main)' }}>100% Local & Confidential</h3>
          <p style={{ fontSize: '0.9rem', color: 'var(--text-muted)' }}>
            Powered by Windows offline OCR and local disk processing. Zero telemetry, zero external cloud APIs, and zero customer leaks.
          </p>
        </div>

        <div className="glass-card">
          <div style={{ fontSize: '1.5rem', marginBottom: '0.75rem' }}>📄</div>
          <h3 style={{ fontSize: '1.1rem', marginBottom: '0.5rem', color: 'var(--text-main)' }}>Pristine Template Preservation</h3>
          <p style={{ fontSize: '0.9rem', color: 'var(--text-muted)' }}>
            Preserves corporate headers, footers, doc classifications, signatures, table styles, and checkbox controls natively.
          </p>
        </div>
      </div>
    </div>
  );
};
