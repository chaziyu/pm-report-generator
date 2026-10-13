import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { getSession, updateField } from '../api/client';
import { Header } from '../components/Header';

export const NewPmPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();

  const [customer, setCustomer] = useState('AEON Credit Services (M) Berhad');
  const [pmDate, setPmDate] = useState('09/09/2026');
  const [fsmsId, setFsmsId] = useState('02936855');
  const [contractNo, setContractNo] = useState('ISS/2021/X2242');
  const [contractPeriod, setContractPeriod] = useState('27/12/2021 - 26/12/2026');
  const [engineerName, setEngineerName] = useState('Cha Zi Yu');
  const [designation, setDesignation] = useState('Associate Technical Engineer');
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (id) {
      getSession(id).then((session) => {
        const meta = session.pm_data?.metadata;
        if (meta?.customer?.value) setCustomer(meta.customer.value);
        if (meta?.pm_date?.value) setPmDate(meta.pm_date.value);
        if (meta?.fsms_id?.value) setFsmsId(meta.fsms_id.value);
        if (meta?.contract_number?.value) setContractNo(meta.contract_number.value);
        if (meta?.contract_period?.value) setContractPeriod(meta.contract_period.value);
        if (meta?.engineer_name?.value) setEngineerName(meta.engineer_name.value);
        if (meta?.engineer_designation?.value) setDesignation(meta.engineer_designation.value);
      }).catch(console.error);
    }
  }, [id]);

  const handleNext = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!id) return;
    setSaving(true);
    try {
      await updateField(id, 'metadata.customer', customer);
      await updateField(id, 'metadata.pm_date', pmDate);
      await updateField(id, 'metadata.fsms_id', fsmsId);
      await updateField(id, 'metadata.contract_number', contractNo);
      await updateField(id, 'metadata.contract_period', contractPeriod);
      await updateField(id, 'metadata.engineer_name', engineerName);
      await updateField(id, 'metadata.engineer_designation', designation);

      navigate(`/session/${id}/upload`);
    } catch (err) {
      console.error(err);
      alert('Failed to save details.');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="app-container">
      <Header currentStep={1} sessionId={id} />

      <div style={{ maxWidth: '680px', margin: '0 auto' }}>
        <div className="glass-card">
          <div style={{ marginBottom: '1.5rem' }}>
            <span style={{ fontSize: '0.85rem', color: '#38bdf8', fontWeight: 600 }}>STEP 1 OF 5</span>
            <h2 style={{ fontSize: '1.6rem', marginTop: '0.25rem' }}>Preventive Maintenance Details</h2>
            <p style={{ color: 'var(--text-muted)', fontSize: '0.95rem' }}>
              Basic customer and contract metadata to be inserted into report cover textboxes and author tables.
            </p>
          </div>

          <form onSubmit={handleNext}>
            <div className="form-group">
              <label className="form-label">Customer Name</label>
              <input 
                type="text" 
                className="form-input" 
                value={customer} 
                onChange={(e) => setCustomer(e.target.value)} 
                required 
              />
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
              <div className="form-group">
                <label className="form-label">PM Date</label>
                <input 
                  type="text" 
                  className="form-input" 
                  value={pmDate} 
                  onChange={(e) => setPmDate(e.target.value)} 
                  required 
                />
              </div>

              <div className="form-group">
                <label className="form-label">FSMS ID</label>
                <input 
                  type="text" 
                  className="form-input" 
                  value={fsmsId} 
                  onChange={(e) => setFsmsId(e.target.value)} 
                  required 
                />
              </div>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
              <div className="form-group">
                <label className="form-label">Contract Number</label>
                <input 
                  type="text" 
                  className="form-input" 
                  value={contractNo} 
                  onChange={(e) => setContractNo(e.target.value)} 
                  required 
                />
              </div>

              <div className="form-group">
                <label className="form-label">Contract Period</label>
                <input 
                  type="text" 
                  className="form-input" 
                  value={contractPeriod} 
                  onChange={(e) => setContractPeriod(e.target.value)} 
                  required 
                />
              </div>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
              <div className="form-group">
                <label className="form-label">Engineer Name</label>
                <input 
                  type="text" 
                  className="form-input" 
                  value={engineerName} 
                  onChange={(e) => setEngineerName(e.target.value)} 
                  required 
                />
              </div>

              <div className="form-group">
                <label className="form-label">Designation</label>
                <input 
                  type="text" 
                  className="form-input" 
                  value={designation} 
                  onChange={(e) => setDesignation(e.target.value)} 
                  required 
                />
              </div>
            </div>

            <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: '1.5rem' }}>
              <button type="submit" className="btn btn-primary" disabled={saving}>
                {saving ? 'Saving...' : 'Next: Upload Screenshots →'}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
};
