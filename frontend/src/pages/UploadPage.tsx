import React, { useState, useEffect, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { getSession, uploadScreenshot } from '../api/client';
import { Header } from '../components/Header';

export const UploadPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const fileInputRef = useRef<HTMLInputElement>(null);

  const [screenshots, setScreenshots] = useState<any[]>([]);
  const [uploading, setUploading] = useState(false);
  const [dragActive, setDragActive] = useState(false);

  const fetchSession = async () => {
    if (!id) return;
    try {
      const data = await getSession(id);
      setScreenshots(data.screenshots || []);
    } catch (err) {
      console.error(err);
    }
  };

  useEffect(() => {
    fetchSession();
  }, [id]);

  const handleFiles = async (files: FileList | null) => {
    if (!files || !id || files.length === 0) return;
    setUploading(true);

    try {
      for (let i = 0; i < files.length; i++) {
        await uploadScreenshot(id, files[i]);
      }
      await fetchSession();
    } catch (err) {
      console.error(err);
      alert('One or more uploads failed.');
    } finally {
      setUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = '';
    }
  };

  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true);
    } else if (e.type === 'dragleave') {
      setDragActive(false);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      handleFiles(e.dataTransfer.files);
    }
  };

  return (
    <div className="app-container">
      <Header currentStep={2} sessionId={id} />

      <div style={{ maxWidth: '880px', margin: '0 auto' }}>
        <div className="glass-card" style={{ marginBottom: '1.5rem' }}>
          <div style={{ marginBottom: '1.25rem' }}>
            <span style={{ fontSize: '0.85rem', color: '#38bdf8', fontWeight: 600 }}>STEP 2 OF 5</span>
            <h2 style={{ fontSize: '1.6rem', marginTop: '0.25rem' }}>Upload Firewall Screenshots</h2>
            <p style={{ color: 'var(--text-muted)', fontSize: '0.95rem' }}>
              Drop all unlabelled firewall screenshots here. No manual category labeling is required.
            </p>
          </div>

          <div
            onDragEnter={handleDrag}
            onDragOver={handleDrag}
            onDragLeave={handleDrag}
            onDrop={handleDrop}
            onClick={() => fileInputRef.current?.click()}
            style={{
              border: `2px dashed ${dragActive ? '#38bdf8' : 'var(--border-color)'}`,
              borderRadius: '12px',
              padding: '2.5rem 1.5rem',
              textAlign: 'center',
              cursor: 'pointer',
              background: dragActive ? 'rgba(56, 189, 248, 0.05)' : 'rgba(15, 23, 42, 0.5)',
              transition: 'all 0.2s',
            }}
          >
            <input 
              type="file" 
              ref={fileInputRef} 
              multiple 
              accept="image/png,image/jpeg" 
              style={{ display: 'none' }} 
              onChange={(e) => handleFiles(e.target.files)} 
            />
            <div style={{ fontSize: '2.5rem', marginBottom: '0.5rem' }}>📁</div>
            <h3 style={{ fontSize: '1.1rem', marginBottom: '0.35rem' }}>
              {uploading ? 'Processing & Normalizing Images...' : 'Drop PNG / JPG screenshots here'}
            </h3>
            <p style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>
              or click to browse from your device
            </p>
          </div>
        </div>

        {screenshots.length > 0 && (
          <div className="glass-card">
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
              <h3 style={{ fontSize: '1.1rem' }}>
                Uploaded Screenshots ({screenshots.length})
              </h3>
              <button 
                className="btn btn-primary"
                onClick={() => navigate(`/session/${id}/analyze`)}
                disabled={uploading}
              >
                Analyze Screenshots →
              </button>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: '1rem' }}>
              {screenshots.map((sc) => {
                const imgUrl = `http://localhost:8000/workspace/${id}/originals/${sc.filename}`;
                return (
                  <div 
                    key={sc.id} 
                    style={{
                      background: 'rgba(15, 23, 42, 0.8)',
                      borderRadius: '8px',
                      overflow: 'hidden',
                      border: '1px solid var(--border-color)',
                      fontSize: '0.8rem',
                    }}
                  >
                    <div style={{ height: '120px', background: '#020617', display: 'flex', alignItems: 'center', justifyContent: 'center', overflow: 'hidden' }}>
                      <img src={imgUrl} alt={sc.filename} style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
                    </div>
                    <div style={{ padding: '0.65rem' }}>
                      <p style={{ fontWeight: 600, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis', marginBottom: '0.35rem' }} title={sc.filename}>
                        {sc.filename}
                      </p>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                        <span style={{ color: 'var(--text-muted)' }}>{sc.width} × {sc.height}</span>
                        {sc.is_duplicate ? (
                          <span className="badge badge-warning">Duplicate</span>
                        ) : (
                          <span className="badge badge-success">Valid</span>
                        )}
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
