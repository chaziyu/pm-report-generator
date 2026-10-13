import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { getSession, generateReport, getDownloadUrl } from '../api/client';
import { Header } from '../components/Header';

export const ResultPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();

  const [session, setSession] = useState<any>(null);
  const [generating, setGenerating] = useState(false);
  const [generatedFile, setGeneratedFile] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (id) {
      getSession(id).then((sess) => {
        setSession(sess);
        if (sess.report_file) {
          setGeneratedFile(sess.report_file);
        }
      }).catch(console.error);
    }
  }, [id]);

  const handleGenerate = async () => {
    if (!id) return;
    setGenerating(true);
    setError(null);
    try {
      const res = await generateReport(id);
      setGeneratedFile(res.filename);
      const updated = await getSession(id);
      setSession(updated);
    } catch (err: any) {
      console.error(err);
      setError(err.message || 'Failed to generate report');
    } finally {
      setGenerating(false);
    }
  };

  const pm = session?.pm_data || {};
  const hasBlockingErrors = session?.validation?.some((v: any) => v.blocking);

  return (
    <div className="app-container">
      <Header currentStep={5} sessionId={id} />

      <div style={{ maxWidth: '680px', margin: '0 auto' }}>
        <div className="glass-card">
          <div style={{ textAlign: 'center', marginBottom: '2rem' }}>
            <span style={{ fontSize: '0.85rem', color: '#38bdf8', fontWeight: 600 }}>STEP 5 OF 5</span>
            <h2 style={{ fontSize: '1.8rem', marginTop: '0.25rem', marginBottom: '0.5rem' }}>
              Generate PM Report
            </h2>
            <p style={{ color: 'var(--text-muted)', fontSize: '0.95rem' }}>
              Finalize telemetry, inject validated evidence into the pristine DOCX template, and produce the official report.
            </p>
          </div>

          {/* Report Summary Card */}
          <div style={{ background: 'rgba(15, 23, 42, 0.7)', borderRadius: '10px', padding: '1.25rem', marginBottom: '1.5rem', border: '1px solid var(--border-color)' }}>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem', fontSize: '0.9rem' }}>
              <div>
                <span style={{ color: 'var(--text-muted)', display: 'block', fontSize: '0.75rem', textTransform: 'uppercase' }}>Customer</span>
                <span style={{ fontWeight: 600 }}>{pm.metadata?.customer?.value || '—'}</span>
              </div>
              <div>
                <span style={{ color: 'var(--text-muted)', display: 'block', fontSize: '0.75rem', textTransform: 'uppercase' }}>PM Date</span>
                <span style={{ fontWeight: 600 }}>{pm.metadata?.pm_date?.value || '—'}</span>
              </div>
              <div>
                <span style={{ color: 'var(--text-muted)', display: 'block', fontSize: '0.75rem', textTransform: 'uppercase' }}>Firewall Model</span>
                <span style={{ fontWeight: 600 }}>{pm.application?.model?.value || '—'}</span>
              </div>
              <div>
                <span style={{ color: 'var(--text-muted)', display: 'block', fontSize: '0.75rem', textTransform: 'uppercase' }}>Hostname</span>
                <span style={{ fontWeight: 600 }}>{pm.application?.hostname?.value || '—'}</span>
              </div>
            </div>
          </div>

          {error && (
            <div style={{ padding: '0.85rem', background: 'rgba(239, 68, 68, 0.1)', border: '1px solid rgba(239, 68, 68, 0.3)', borderRadius: '8px', color: '#f87171', marginBottom: '1.5rem', fontSize: '0.9rem' }}>
              {error}
            </div>
          )}

          {generatedFile ? (
            <div style={{ textAlign: 'center', padding: '1.5rem 0' }}>
              <div style={{ fontSize: '3rem', marginBottom: '0.5rem' }}>🎉</div>
              <h3 style={{ fontSize: '1.3rem', color: '#34d399', marginBottom: '0.5rem' }}>
                Report Generated Successfully!
              </h3>
              <p style={{ color: 'var(--text-muted)', fontSize: '0.9rem', marginBottom: '1.5rem' }}>
                {generatedFile}
              </p>

              <div style={{ display: 'flex', justifyContent: 'center', gap: '1rem' }}>
                <a 
                  href={getDownloadUrl(id!)} 
                  className="btn btn-primary"
                  download
                  style={{ padding: '0.8rem 1.8rem', fontSize: '1rem' }}
                >
                  📥 Download DOCX Report
                </a>
                <button 
                  className="btn btn-secondary" 
                  onClick={() => navigate('/')}
                >
                  + New Report
                </button>
              </div>
            </div>
          ) : (
            <div style={{ textAlign: 'center' }}>
              <button 
                className="btn btn-primary"
                onClick={handleGenerate}
                disabled={generating || hasBlockingErrors}
                style={{ width: '100%', padding: '0.85rem 1.5rem', fontSize: '1.05rem' }}
              >
                {generating ? 'Injecting Telemetry & Compiling DOCX...' : 'Generate PM Report (.docx)'}
              </button>
              {hasBlockingErrors && (
                <p style={{ color: '#f87171', fontSize: '0.85rem', marginTop: '0.75rem' }}>
                  ⚠ Generation is disabled until blocking validation errors in Step 4 are resolved.
                </p>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
