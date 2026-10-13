import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { getSession, updateField } from '../api/client';
import { Header } from '../components/Header';

export const ReviewPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();

  const [session, setSession] = useState<any>(null);
  const [activeTab, setActiveTab] = useState<'data' | 'appendices' | 'validation'>('data');
  const [selectedField, setSelectedField] = useState<{
    label: string;
    path: string;
    valObj: any;
    section: string;
  } | null>(null);

  const [selectedAppendix, setSelectedAppendix] = useState<number | null>(1);
  const [editValue, setEditValue] = useState<any>('');

  const fetchSession = async () => {
    if (!id) return;
    try {
      const data = await getSession(id);
      setSession(data);
      if (!selectedField && data.pm_data?.hardware?.cpu_usage) {
        setSelectedField({
          label: 'CPU Usage',
          path: 'hardware.cpu_usage',
          valObj: data.pm_data.hardware.cpu_usage,
          section: 'hardware',
        });
        setEditValue(data.pm_data.hardware.cpu_usage.value ?? '');
      }
    } catch (err) {
      console.error(err);
    }
  };

  useEffect(() => {
    fetchSession();
  }, [id]);

  const handleSelectField = (label: string, path: string, valObj: any, section: string) => {
    setSelectedField({ label, path, valObj, section });
    setEditValue(valObj?.value ?? '');
  };

  const handleSaveFieldEdit = async () => {
    if (!id || !selectedField) return;
    try {
      await updateField(id, selectedField.path, editValue);
      await fetchSession();
    } catch (err) {
      console.error(err);
      alert('Failed to update field.');
    }
  };

  const pm = session?.pm_data || {};
  const screenshots = session?.screenshots || [];
  const validation = session?.validation || [];
  const appendices = pm.appendices || {};

  // Find source screenshot for currently selected field or appendix
  let currentImageSrc = '';
  let currentImageCaption = '';
  let currentConfidence = 0;
  let sourceText = '';

  if (activeTab === 'appendices' && selectedAppendix) {
    const appEv = appendices[selectedAppendix];
    if (appEv?.crop_path) {
      const cropFilename = appEv.crop_path.split(/[\\/]/).pop();
      currentImageSrc = `http://localhost:8000/workspace/${id}/crops/${cropFilename}`;
      currentImageCaption = `${appEv.title} (Crop)`;
      currentConfidence = appEv.confidence;
    } else if (appEv?.screenshot_ids?.length > 0) {
      const sc = screenshots.find((s: any) => s.id === appEv.screenshot_ids[0]);
      if (sc) {
        currentImageSrc = `http://localhost:8000/workspace/${id}/originals/${sc.filename}`;
        currentImageCaption = `${appEv.title} (Full)`;
        currentConfidence = appEv.confidence;
      }
    }
  } else if (selectedField?.valObj) {
    const scId = selectedField.valObj.source_screenshot_id;
    const sc = screenshots.find((s: any) => s.id === scId);
    if (sc) {
      currentImageSrc = `http://localhost:8000/workspace/${id}/originals/${sc.filename}`;
      currentImageCaption = sc.filename;
    }
    currentConfidence = selectedField.valObj.confidence || 0;
    sourceText = selectedField.valObj.source_text || '';
  }

  return (
    <div className="app-container">
      <Header currentStep={4} sessionId={id} />

      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.25rem' }}>
        <div>
          <span style={{ fontSize: '0.85rem', color: '#38bdf8', fontWeight: 600 }}>STEP 4 OF 5</span>
          <h2 style={{ fontSize: '1.6rem', marginTop: '0.25rem' }}>Review PM Telemetry & Evidence</h2>
        </div>

        <button 
          className="btn btn-primary"
          onClick={() => navigate(`/session/${id}/result`)}
        >
          Proceed to Generate Report →
        </button>
      </div>

      <div className="two-col-layout">
        {/* Left Column: Review Tabs */}
        <div className="glass-card">
          {/* Tab Navigation */}
          <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '1.25rem', borderBottom: '1px solid var(--border-color)', paddingBottom: '0.75rem' }}>
            <button 
              className={`btn ${activeTab === 'data' ? 'btn-primary' : 'btn-secondary'}`}
              style={{ fontSize: '0.85rem', padding: '0.45rem 1rem' }}
              onClick={() => setActiveTab('data')}
            >
              Extracted Data
            </button>
            <button 
              className={`btn ${activeTab === 'appendices' ? 'btn-primary' : 'btn-secondary'}`}
              style={{ fontSize: '0.85rem', padding: '0.45rem 1rem' }}
              onClick={() => setActiveTab('appendices')}
            >
              Appendices (1–16)
            </button>
            <button 
              className={`btn ${activeTab === 'validation' ? 'btn-primary' : 'btn-secondary'}`}
              style={{ fontSize: '0.85rem', padding: '0.45rem 1rem' }}
              onClick={() => setActiveTab('validation')}
            >
              Validation ({validation.length})
            </button>
          </div>

          {/* TAB 1: Extracted Data */}
          {activeTab === 'data' && (
            <div style={{ maxHeight: '600px', overflowY: 'auto', paddingRight: '0.5rem' }}>
              {/* Application Information */}
              <div style={{ marginBottom: '1.5rem' }}>
                <h4 style={{ fontSize: '0.85rem', textTransform: 'uppercase', color: '#38bdf8', marginBottom: '0.75rem' }}>
                  Application Info
                </h4>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                  {[
                    { label: 'Hostname', path: 'application.hostname', val: pm.application?.hostname },
                    { label: 'Model', path: 'application.model', val: pm.application?.model },
                    { label: 'Serial (Primary)', path: 'application.serial_primary', val: pm.application?.serial_primary },
                    { label: 'Serial (Secondary)', path: 'application.serial_secondary', val: pm.application?.serial_secondary },
                  ].map((f) => (
                    <div 
                      key={f.path}
                      onClick={() => handleSelectField(f.label, f.path, f.val, 'application')}
                      style={{
                        padding: '0.65rem 0.85rem',
                        background: selectedField?.path === f.path ? 'rgba(56, 189, 248, 0.15)' : 'rgba(15, 23, 42, 0.5)',
                        border: `1px solid ${selectedField?.path === f.path ? '#38bdf8' : 'var(--border-color)'}`,
                        borderRadius: '6px',
                        cursor: 'pointer',
                        display: 'flex',
                        justifyContent: 'space-between',
                        alignItems: 'center',
                      }}
                    >
                      <span style={{ fontSize: '0.9rem', color: 'var(--text-muted)' }}>{f.label}</span>
                      <span style={{ fontWeight: 600 }}>{f.val?.value || '—'}</span>
                    </div>
                  ))}
                </div>
              </div>

              {/* Hardware Health */}
              <div style={{ marginBottom: '1.5rem' }}>
                <h4 style={{ fontSize: '0.85rem', textTransform: 'uppercase', color: '#38bdf8', marginBottom: '0.75rem' }}>
                  Hardware Telemetry
                </h4>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                  {[
                    { label: 'CPU Usage', path: 'hardware.cpu_usage', val: pm.hardware?.cpu_usage, suffix: '%' },
                    { label: 'CPU Status', path: 'hardware.cpu_status', val: pm.hardware?.cpu_status },
                    { label: 'Memory Usage', path: 'hardware.memory_usage', val: pm.hardware?.memory_usage, suffix: '%' },
                    { label: 'Memory Status', path: 'hardware.memory_status', val: pm.hardware?.memory_status },
                  ].map((f) => (
                    <div 
                      key={f.path}
                      onClick={() => handleSelectField(f.label, f.path, f.val, 'hardware')}
                      style={{
                        padding: '0.65rem 0.85rem',
                        background: selectedField?.path === f.path ? 'rgba(56, 189, 248, 0.15)' : 'rgba(15, 23, 42, 0.5)',
                        border: `1px solid ${selectedField?.path === f.path ? '#38bdf8' : 'var(--border-color)'}`,
                        borderRadius: '6px',
                        cursor: 'pointer',
                        display: 'flex',
                        justifyContent: 'space-between',
                        alignItems: 'center',
                      }}
                    >
                      <span style={{ fontSize: '0.9rem', color: 'var(--text-muted)' }}>{f.label}</span>
                      <span style={{ fontWeight: 600 }}>
                        {f.val?.value !== null && f.val?.value !== undefined ? `${f.val.value}${f.suffix || ''}` : '—'}
                      </span>
                    </div>
                  ))}
                </div>
              </div>

              {/* Firmware & Licensing */}
              <div style={{ marginBottom: '1.5rem' }}>
                <h4 style={{ fontSize: '0.85rem', textTransform: 'uppercase', color: '#38bdf8', marginBottom: '0.75rem' }}>
                  Firmware & Licensing
                </h4>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                  {[
                    { label: 'Current Firmware', path: 'firmware.current', val: pm.firmware?.current },
                    { label: 'Firmware Build', path: 'firmware.build', val: pm.firmware?.build },
                    { label: 'Firmware Status', path: 'firmware.status', val: pm.firmware?.status },
                    { label: 'FortiCare Status', path: 'licensing.forticare_status', val: pm.licensing?.forticare_status },
                    { label: 'License Expiry', path: 'licensing.expiry_date', val: pm.licensing?.expiry_date },
                  ].map((f) => (
                    <div 
                      key={f.path}
                      onClick={() => handleSelectField(f.label, f.path, f.val, 'firmware')}
                      style={{
                        padding: '0.65rem 0.85rem',
                        background: selectedField?.path === f.path ? 'rgba(56, 189, 248, 0.15)' : 'rgba(15, 23, 42, 0.5)',
                        border: `1px solid ${selectedField?.path === f.path ? '#38bdf8' : 'var(--border-color)'}`,
                        borderRadius: '6px',
                        cursor: 'pointer',
                        display: 'flex',
                        justifyContent: 'space-between',
                        alignItems: 'center',
                      }}
                    >
                      <span style={{ fontSize: '0.9rem', color: 'var(--text-muted)' }}>{f.label}</span>
                      <span style={{ fontWeight: 600 }}>{f.val?.value || '—'}</span>
                    </div>
                  ))}
                </div>
              </div>

              {/* VPN & Configuration */}
              <div>
                <h4 style={{ fontSize: '0.85rem', textTransform: 'uppercase', color: '#38bdf8', marginBottom: '0.75rem' }}>
                  VPN & Operations
                </h4>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                  {[
                    { label: 'VPN Tunnels (Total)', path: 'vpn.total', val: pm.vpn?.total },
                    { label: 'VPN Tunnels (Active)', path: 'vpn.active', val: pm.vpn?.active },
                    { label: 'System Uptime', path: 'configuration.uptime', val: pm.configuration?.uptime },
                    { label: 'High Availability', path: 'configuration.ha_status', val: pm.configuration?.ha_status },
                    { label: 'Backup Status', path: 'configuration.backup_status', val: pm.configuration?.backup_status },
                  ].map((f) => (
                    <div 
                      key={f.path}
                      onClick={() => handleSelectField(f.label, f.path, f.val, 'configuration')}
                      style={{
                        padding: '0.65rem 0.85rem',
                        background: selectedField?.path === f.path ? 'rgba(56, 189, 248, 0.15)' : 'rgba(15, 23, 42, 0.5)',
                        border: `1px solid ${selectedField?.path === f.path ? '#38bdf8' : 'var(--border-color)'}`,
                        borderRadius: '6px',
                        cursor: 'pointer',
                        display: 'flex',
                        justifyContent: 'space-between',
                        alignItems: 'center',
                      }}
                    >
                      <span style={{ fontSize: '0.9rem', color: 'var(--text-muted)' }}>{f.label}</span>
                      <span style={{ fontWeight: 600 }}>{f.val?.value !== null && f.val?.value !== undefined ? String(f.val.value) : '—'}</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* TAB 2: Appendices */}
          {activeTab === 'appendices' && (
            <div style={{ maxHeight: '600px', overflowY: 'auto' }}>
              {Array.from({ length: 16 }, (_, i) => i + 1).map((num) => {
                const appEv = appendices[num] || {};
                const isSelected = selectedAppendix === num;
                const hasEvidence = appEv.screenshot_ids && appEv.screenshot_ids.length > 0;

                return (
                  <div
                    key={num}
                    onClick={() => setSelectedAppendix(num)}
                    style={{
                      padding: '0.75rem 1rem',
                      background: isSelected ? 'rgba(56, 189, 248, 0.15)' : 'rgba(15, 23, 42, 0.4)',
                      border: `1px solid ${isSelected ? '#38bdf8' : 'var(--border-color)'}`,
                      borderRadius: '6px',
                      marginBottom: '0.5rem',
                      cursor: 'pointer',
                      display: 'flex',
                      justifyContent: 'space-between',
                      alignItems: 'center',
                    }}
                  >
                    <div>
                      <div style={{ fontWeight: 600, fontSize: '0.9rem' }}>
                        Appendix {num}: {appEv.title}
                      </div>
                      <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                        {hasEvidence ? `Evidence: ${appEv.screenshot_ids[0]}` : 'Missing screenshot evidence'}
                      </div>
                    </div>
                    {hasEvidence ? (
                      <span className="badge badge-success">Assigned</span>
                    ) : (
                      <span className="badge badge-warning">Missing</span>
                    )}
                  </div>
                );
              })}
            </div>
          )}

          {/* TAB 3: Validation */}
          {activeTab === 'validation' && (
            <div style={{ maxHeight: '600px', overflowY: 'auto' }}>
              {validation.length === 0 ? (
                <div style={{ padding: '2rem', textAlign: 'center', color: '#34d399' }}>
                  ✓ All consistency checks passed. Ready for report generation!
                </div>
              ) : (
                validation.map((v: any, idx: number) => (
                  <div 
                    key={idx}
                    style={{
                      padding: '0.75rem 1rem',
                      background: v.severity === 'ERROR' ? 'rgba(239, 68, 68, 0.1)' : 'rgba(245, 158, 11, 0.1)',
                      border: `1px solid ${v.severity === 'ERROR' ? 'rgba(239, 68, 68, 0.3)' : 'rgba(245, 158, 11, 0.3)'}`,
                      borderRadius: '8px',
                      marginBottom: '0.5rem',
                      fontSize: '0.85rem',
                    }}
                  >
                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.25rem' }}>
                      <span style={{ fontWeight: 700, color: v.severity === 'ERROR' ? '#f87171' : '#fbbf24' }}>
                        {v.severity} {v.blocking ? '(Blocking)' : ''}
                      </span>
                      {v.appendix_number && <span>Appendix {v.appendix_number}</span>}
                    </div>
                    <div>{v.message}</div>
                  </div>
                ))
              )}
            </div>
          )}
        </div>

        {/* Right Column: Evidence Inspector */}
        <div className="glass-card">
          <div style={{ borderBottom: '1px solid var(--border-color)', paddingBottom: '0.75rem', marginBottom: '1rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <div>
              <h3 style={{ fontSize: '1.1rem' }}>Evidence Inspector</h3>
              <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                {activeTab === 'appendices' ? `Viewing Appendix ${selectedAppendix}` : selectedField?.label}
              </p>
            </div>
            {currentConfidence > 0 && (
              <span className="badge badge-info">
                {Math.round(currentConfidence * 100)}% Confidence
              </span>
            )}
          </div>

          {/* Multi-Category and Evidence Status Banner (Section 21) */}
          {activeTab === 'appendices' && selectedAppendix && (() => {
            const appEv = appendices[selectedAppendix];
            const sc = screenshots.find((s: any) => s.id === appEv?.screenshot_ids?.[0]);
            if (!sc) return null;

            const isMulti = sc.assigned_categories && sc.assigned_categories.length > 1;
            const isMismatch = sc.mismatch_warning || (sc.source_content_status === 'SOURCE_CONTENT_MISFILED');

            return (
              <div style={{ marginBottom: '1rem' }}>
                {isMulti && (
                  <div style={{ background: 'rgba(56, 189, 248, 0.08)', border: '1px solid rgba(56, 189, 248, 0.3)', borderRadius: '8px', padding: '0.65rem 0.85rem', marginBottom: '0.5rem', fontSize: '0.8rem' }}>
                    <div style={{ fontWeight: 600, color: '#38bdf8', marginBottom: '0.25rem' }}>✓ Multiple Valid Categories Evidenced:</div>
                    <div style={{ display: 'flex', gap: '0.4rem', flexWrap: 'wrap' }}>
                      {sc.assigned_categories.map((c: string) => (
                        <span key={c} className="badge badge-info" style={{ fontSize: '0.75rem', textTransform: 'capitalize' }}>
                          ✓ {c.replace(/_/g, ' ')}
                        </span>
                      ))}
                    </div>
                    <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '0.35rem' }}>
                      Evidence legitimately serves multiple PM report appendices.
                    </div>
                  </div>
                )}

                {isMismatch && (
                  <div style={{ background: 'rgba(239, 68, 68, 0.08)', border: '1px solid rgba(239, 68, 68, 0.3)', borderRadius: '8px', padding: '0.65rem 0.85rem', fontSize: '0.8rem' }}>
                    <div style={{ fontWeight: 600, color: '#f87171', marginBottom: '0.25rem' }}>⚠️ Source Evidence Mismatch:</div>
                    <div style={{ color: 'var(--text-muted)' }}>
                      Expected caption: <code>{sc.source_caption_category || 'Unknown'}</code>
                    </div>
                    <div style={{ color: '#34d399', marginTop: '0.2rem' }}>
                      Detected content: <strong>{sc.assigned_categories?.join(', ') || 'None'}</strong>
                    </div>
                  </div>
                )}
              </div>
            );
          })()}

          {/* Conflict Resolution Card (Section 27) */}
          {activeTab === 'data' && selectedField?.valObj && (
            (selectedField.valObj.arbitration_state === 'DISAGREEMENT' || 
             (selectedField.valObj.ai_value !== undefined && selectedField.valObj.ai_value !== null && String(selectedField.valObj.ai_value) !== String(selectedField.valObj.value))) ? (
              <div style={{ background: 'rgba(239, 68, 68, 0.08)', border: '1px solid rgba(239, 68, 68, 0.3)', borderRadius: '8px', padding: '0.85rem 1rem', marginBottom: '1rem' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5rem' }}>
                  <span style={{ fontWeight: 700, color: '#f87171', fontSize: '0.85rem' }}>⚠️ Values Disagree</span>
                  <span className="badge badge-warning" style={{ fontSize: '0.7rem' }}>Manual Confirmation Required</span>
                </div>
                <div style={{ fontSize: '0.85rem', marginBottom: '0.5rem', display: 'flex', flexDirection: 'column', gap: '0.25rem' }}>
                  <div><strong>OCR / Detected:</strong> <code style={{ color: '#38bdf8', background: 'rgba(15, 23, 42, 0.8)', padding: '0.1rem 0.3rem', borderRadius: '4px' }}>{String(selectedField.valObj?.value ?? 'None')}</code></div>
                  <div><strong>Local AI Suggestion:</strong> <code style={{ color: '#34d399', background: 'rgba(15, 23, 42, 0.8)', padding: '0.1rem 0.3rem', borderRadius: '4px' }}>{String(selectedField.valObj?.ai_value ?? 'None')}</code></div>
                </div>
                {(selectedField.path.includes('serial') || selectedField.path.includes('hostname')) && (
                  <div style={{ fontSize: '0.75rem', color: '#fbbf24', marginBottom: '0.6rem', background: 'rgba(245, 158, 11, 0.1)', border: '1px solid rgba(245, 158, 11, 0.2)', padding: '0.4rem 0.6rem', borderRadius: '4px' }}>
                    ⚠️ <strong>Critical Identifier</strong>: Never silently accept AI modifications. Confirm value against hardware sticker or support portal.
                  </div>
                )}
                <div style={{ display: 'flex', gap: '0.5rem', marginTop: '0.5rem' }}>
                  <button 
                    className="btn btn-secondary" 
                    style={{ fontSize: '0.8rem', padding: '0.35rem 0.75rem' }}
                    onClick={async () => {
                      setEditValue(selectedField.valObj?.value ?? '');
                      await updateField(id!, selectedField.path, selectedField.valObj?.value);
                      await fetchSession();
                    }}
                  >
                    [Use Detected]
                  </button>
                  <button 
                    className="btn btn-primary" 
                    style={{ fontSize: '0.8rem', padding: '0.35rem 0.75rem' }}
                    onClick={async () => {
                      if (selectedField.valObj?.ai_value !== undefined) {
                        setEditValue(selectedField.valObj.ai_value);
                        await updateField(id!, selectedField.path, selectedField.valObj.ai_value);
                        await fetchSession();
                      }
                    }}
                  >
                    [Use AI Suggestion]
                  </button>
                  <button 
                    className="btn btn-secondary" 
                    style={{ fontSize: '0.8rem', padding: '0.35rem 0.75rem' }}
                    onClick={() => {
                      const input = document.getElementById('field-edit-input');
                      if (input) input.focus();
                    }}
                  >
                    [Enter Manually]
                  </button>
                </div>
              </div>
            ) : selectedField.valObj.arbitration_state === 'AI_VERIFIED' ? (
              <div style={{ background: 'rgba(16, 185, 129, 0.08)', border: '1px solid rgba(16, 185, 129, 0.25)', borderRadius: '8px', padding: '0.6rem 0.85rem', marginBottom: '1rem', fontSize: '0.8rem', color: '#34d399', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <span>✓</span>
                <span>Local AI verified: Output agrees with deterministic extraction.</span>
              </div>
            ) : null
          )}

          {/* Inline Edit Panel when a field is selected */}
          {activeTab === 'data' && selectedField && (
            <div style={{ background: 'rgba(15, 23, 42, 0.7)', padding: '0.75rem', borderRadius: '8px', marginBottom: '1rem', border: '1px solid var(--border-color)' }}>
              <label className="form-label" style={{ marginBottom: '0.25rem' }}>Edit {selectedField.label}</label>
              <div style={{ display: 'flex', gap: '0.5rem' }}>
                <input 
                  id="field-edit-input"
                  type="text" 
                  className="form-input" 
                  value={editValue} 
                  onChange={(e) => setEditValue(e.target.value)}
                  style={{ padding: '0.45rem 0.75rem' }} 
                />
                <button className="btn btn-primary" onClick={handleSaveFieldEdit} style={{ padding: '0.45rem 1rem', fontSize: '0.85rem' }}>
                  Save
                </button>
              </div>
              {sourceText && (
                <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '0.4rem' }}>
                  OCR source: "{sourceText}"
                </div>
              )}
            </div>
          )}

          {/* Screenshot Preview */}
          <div style={{ minHeight: '340px', background: '#020617', borderRadius: '8px', overflow: 'hidden', border: '1px solid var(--border-color)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            {currentImageSrc ? (
              <img 
                src={currentImageSrc} 
                alt="Evidence" 
                style={{ maxWidth: '100%', maxHeight: '420px', objectFit: 'contain' }} 
              />
            ) : (
              <div style={{ color: 'var(--text-muted)', fontSize: '0.9rem' }}>
                No screenshot linked to this field
              </div>
            )}
          </div>
          {currentImageCaption && (
            <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginTop: '0.5rem', textAlign: 'center' }}>
              Source: {currentImageCaption}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
