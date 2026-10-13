import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { getSession, runAnalysis, getAiStatus, startAiSetup, cancelAiDownload, cancelRuntimeInstall } from '../api/client';
import { Header } from '../components/Header';

export const AnalysisPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();

  const [session, setSession] = useState<any>(null);
  const [analyzing, setAnalyzing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [aiStatus, setAiStatus] = useState<any>(null);
  const [downloadingAi, setDownloadingAi] = useState(false);

  const fetchAiStatus = async () => {
    try {
      const status = await getAiStatus();
      setAiStatus(status);
      if (status.status === 'INSTALLING' || status.status === 'INSTALLING_RUNTIME') {
        setDownloadingAi(true);
      } else {
        setDownloadingAi(false);
      }
    } catch (e) {
      console.warn('AI status check failed', e);
    }
  };

  useEffect(() => {
    fetchAiStatus();
    const interval = setInterval(fetchAiStatus, 3000);
    return () => clearInterval(interval);
  }, []);

  const handleStartAiSetup = async () => {
    try {
      await startAiSetup();
      setDownloadingAi(true);
      fetchAiStatus();
    } catch (err: any) {
      alert(err.message || 'Failed to start Local AI setup');
    }
  };

  const handleCancelAiSetup = async () => {
    try {
      if (aiStatus?.status === 'INSTALLING_RUNTIME') {
        await cancelRuntimeInstall();
      } else {
        await cancelAiDownload();
      }
      setDownloadingAi(false);
      fetchAiStatus();
    } catch (err: any) {
      alert(err.message || 'Failed to cancel setup');
    }
  };


  const startAnalysis = async () => {
    if (!id) return;
    setAnalyzing(true);
    setError(null);
    try {
      const data = await runAnalysis(id);
      setSession(data);
    } catch (err: any) {
      console.error(err);
      setError(err.message || 'Analysis failed');
    } finally {
      setAnalyzing(false);
    }
  };

  useEffect(() => {
    if (id) {
      getSession(id).then((sess) => {
        setSession(sess);
        if (sess.status === 'UPLOADED') {
          startAnalysis();
        }
      }).catch(console.error);
    }
  }, [id]);

  const appendices = session?.pm_data?.appendices || {};
  const totalAppendices = Object.keys(appendices).length || 16;
  const detectedCount = Object.values(appendices).filter((a: any) => a.screenshot_ids && a.screenshot_ids.length > 0).length;

  const screenshots = session?.screenshots || [];
  const ambiguousScreenshots = screenshots.filter((s: any) => s.is_ambiguous || (s.ambiguity_reasons && s.ambiguity_reasons.length > 0));
  const ambiguousCount = ambiguousScreenshots.length;


  return (
    <div className="app-container">
      <Header currentStep={3} sessionId={id} />

      <div style={{ maxWidth: '880px', margin: '0 auto' }}>
        <div className="glass-card" style={{ marginBottom: '1.5rem' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.25rem' }}>
            <div>
              <span style={{ fontSize: '0.85rem', color: '#38bdf8', fontWeight: 600 }}>STEP 3 OF 5</span>
              <h2 style={{ fontSize: '1.6rem', marginTop: '0.25rem' }}>Screenshot Analysis</h2>
              <p style={{ color: 'var(--text-muted)', fontSize: '0.95rem' }}>
                Automated classification, OCR telemetry extraction, and appendix container mapping.
              </p>
            </div>
            {analyzing ? (
              <div className="badge badge-info" style={{ fontSize: '0.85rem', padding: '0.4rem 0.8rem' }}>
                Analyzing...
              </div>
            ) : (
              <button className="btn btn-secondary" onClick={startAnalysis} style={{ fontSize: '0.85rem' }}>
                ↻ Re-run Analysis
              </button>
            )}
          </div>

          {error && (
            <div style={{ padding: '0.85rem', background: 'rgba(239, 68, 68, 0.1)', border: '1px solid rgba(239, 68, 68, 0.3)', borderRadius: '8px', color: '#f87171', marginBottom: '1rem', fontSize: '0.9rem' }}>
              Error: {error}
            </div>
          )}

          {/* Local AI Setup / Status Banner (Section 32) */}
          {(aiStatus?.status === 'RUNTIME_MISSING' || aiStatus?.status === 'MODEL_MISSING' || aiStatus?.status === 'INSTALLING_RUNTIME' || downloadingAi) && (
            <div style={{ background: 'rgba(56, 189, 248, 0.08)', border: '1px solid rgba(56, 189, 248, 0.25)', borderRadius: '8px', padding: '1rem', marginBottom: '1.25rem' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5rem' }}>
                <div>
                  <div style={{ fontWeight: 600, color: '#38bdf8' }}>
                    {downloadingAi ? 'Setting up Local AI' : 'Local AI setup required'}
                  </div>
                  <div style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>
                    Optional local interpretation component for ambiguous screenshots and fallback verification.
                  </div>
                </div>
                {!downloadingAi ? (
                  <button className="btn btn-primary" onClick={handleStartAiSetup} style={{ fontSize: '0.8rem', padding: '0.4rem 0.8rem' }}>
                    Set up Local AI
                  </button>
                ) : (
                  <button className="btn btn-secondary" onClick={handleCancelAiSetup} style={{ fontSize: '0.8rem', padding: '0.4rem 0.8rem' }}>
                    Cancel
                  </button>
                )}
              </div>
              {downloadingAi && (
                <div style={{ marginTop: '0.75rem' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.8rem', marginBottom: '0.25rem' }}>
                    <span>{aiStatus?.message || 'Setting up Local AI...'}</span>
                    <span>{aiStatus?.progress ? `${Math.round(aiStatus.progress)}%` : 'Processing...'}</span>
                  </div>
                  <div style={{ height: '6px', background: 'rgba(148, 163, 184, 0.2)', borderRadius: '9999px', overflow: 'hidden' }}>
                    <div 
                      style={{ 
                        height: '100%', 
                        width: `${aiStatus?.progress || 15}%`, 
                        background: '#38bdf8',
                        transition: 'width 0.3s ease'
                      }} 
                    />
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Local AI Verification Indicator */}
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', background: 'rgba(15, 23, 42, 0.4)', border: '1px solid var(--border-color)', borderRadius: '8px', padding: '0.6rem 1rem', marginBottom: '1rem', fontSize: '0.85rem' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <span style={{ 
                width: '8px', 
                height: '8px', 
                borderRadius: '50%', 
                background: (aiStatus?.status === 'READY' || aiStatus?.status === 'RUNNING' || aiStatus?.status === 'IDLE') ? '#34d399' : '#f59e0b',
                display: 'inline-block'
              }} />
              <span style={{ fontWeight: 600 }}>Local AI Assistance</span>
            </div>

            <div>
              {aiStatus?.status === 'DISABLED' || aiStatus?.status === 'UNAVAILABLE' ? (
                <span style={{ color: '#f59e0b' }}>Local AI assistance unavailable. Affected fields require manual review.</span>
              ) : ambiguousCount > 0 ? (
                <span style={{ color: '#38bdf8', fontWeight: 600 }}>
                  Local AI verification: {ambiguousCount} ambiguous screenshot{ambiguousCount > 1 ? 's' : ''} checked
                </span>
              ) : (
                <span style={{ color: 'var(--text-muted)' }}>
                  Local AI verification: Not required (High confidence & clear)
                </span>
              )}
            </div>
          </div>

          <div style={{ background: 'rgba(15, 23, 42, 0.6)', padding: '1rem', borderRadius: '8px', marginBottom: '1.5rem' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.5rem', fontSize: '0.9rem' }}>
              <span>Appendix Coverage</span>
              <span style={{ fontWeight: 700, color: '#38bdf8' }}>{detectedCount} / {totalAppendices} detected</span>
            </div>
            <div style={{ height: '8px', background: 'rgba(148, 163, 184, 0.2)', borderRadius: '9999px', overflow: 'hidden' }}>
              <div 
                style={{ 
                  height: '100%', 
                  width: `${(detectedCount / totalAppendices) * 100}%`, 
                  background: 'linear-gradient(90deg, #38bdf8 0%, #10b981 100%)',
                  transition: 'width 0.4s ease'
                }} 
              />
            </div>
          </div>

          {/* Appendix Checklist */}
          <div style={{ border: '1px solid var(--border-color)', borderRadius: '8px', overflow: 'hidden' }}>
            <div style={{ padding: '0.75rem 1rem', background: 'rgba(15, 23, 42, 0.8)', fontWeight: 600, fontSize: '0.85rem', color: 'var(--text-muted)', display: 'grid', gridTemplateColumns: '60px 1fr 140px 100px' }}>
              <span>APP #</span>
              <span>TITLE & EVIDENCE</span>
              <span>CONFIDENCE</span>
              <span>STATUS</span>
            </div>

            <div style={{ maxHeight: '420px', overflowY: 'auto' }}>
              {Array.from({ length: 16 }, (_, i) => i + 1).map((num) => {
                const appEv = appendices[num] || {};
                const hasEvidence = appEv.screenshot_ids && appEv.screenshot_ids.length > 0;
                const confPercent = Math.round((appEv.confidence || 0) * 100);

                return (
                  <div 
                    key={num}
                    style={{
                      padding: '0.75rem 1rem',
                      display: 'grid',
                      gridTemplateColumns: '60px 1fr 140px 100px',
                      alignItems: 'center',
                      borderTop: '1px solid var(--border-color)',
                      fontSize: '0.9rem',
                      background: hasEvidence ? 'transparent' : 'rgba(239, 68, 68, 0.03)',
                    }}
                  >
                    <span style={{ fontWeight: 700, color: hasEvidence ? '#38bdf8' : 'var(--text-muted)' }}>
                      #{num}
                    </span>
                    <div>
                      <div style={{ fontWeight: 600 }}>{appEv.title || `Appendix ${num}`}</div>
                      <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                        {hasEvidence ? `Assigned image: ${appEv.screenshot_ids[0]}` : 'No evidence matched'}
                      </div>
                    </div>
                    <div>
                      {hasEvidence ? (
                        <span style={{ fontWeight: 600, color: confPercent >= 85 ? '#34d399' : '#fbbf24' }}>
                          {confPercent}%
                        </span>
                      ) : (
                        <span style={{ color: 'var(--text-muted)' }}>—</span>
                      )}
                    </div>
                    <div>
                      {hasEvidence ? (
                        <span className="badge badge-success">Detected</span>
                      ) : (
                        <span className="badge badge-warning">Missing</span>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: '1.5rem' }}>
            <button 
              className="btn btn-primary"
              onClick={() => navigate(`/session/${id}/review`)}
              disabled={analyzing}
            >
              Continue to Review →
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
