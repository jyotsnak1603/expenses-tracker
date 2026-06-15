import { useState, useRef, useEffect } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import api from '../api/axios';

export default function ImportCSV() {
  const { groupId } = useParams();
  const navigate = useNavigate();
  const [file, setFile] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [session, setSession] = useState(null);
  const [activeIssue, setActiveIssue] = useState(null);
  const [customValue, setCustomValue] = useState('');
  const [confirming, setConfirming] = useState(false);
  const [importError, setImportError] = useState(null);
  const fileInputRef = useRef(null);

  const handleFileChange = (e) => {
    if (e.target.files[0]) {
      setFile(e.target.files[0]);
    }
  };

  const handleUpload = async () => {
    if (!file) return;
    setUploading(true);
    const formData = new FormData();
    formData.append('file', file);
    
    try {
      const res = await api.post(`/import/group/${groupId}/upload/`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
      setSession(res.data);
      // Auto-accept info/auto-fixes to save user time
      if (res.data.issue_summary.auto_fixed > 0 || res.data.issue_summary.info > 0) {
        await api.post(`/import/${res.data.id}/resolve-auto/`);
        const updated = await api.get(`/import/${res.data.id}/`);
        setSession(updated.data);
      }
    } catch (err) {
      setImportError(err.response?.data?.error || 'Upload failed');
    } finally {
      setUploading(false);
    }
  };

  const handleResolve = async (issueId, resolution, value = '') => {
    try {
      await api.patch(`/import/${session.id}/issues/${issueId}/`, {
        resolution,
        user_value: value
      });
      
      // Refresh session
      const res = await api.get(`/import/${session.id}/`);
      setSession(res.data);
      setActiveIssue(null);
      setCustomValue('');
    } catch (err) {
      console.error(err);
    }
  };

  const handleConfirmImport = async () => {
    setConfirming(true);
    setImportError(null);
    try {
      await api.post(`/import/${session.id}/confirm/`);
      navigate(`/groups/${groupId}`);
    } catch (err) {
      setImportError(err.response?.data?.error || 'Import failed');
      setConfirming(false);
    }
  };

  // If we haven't uploaded yet
  if (!session) {
    return (
      <div className="min-h-screen pt-20 flex justify-center items-center px-4">
        <motion.div initial={{opacity:0, scale:0.95}} animate={{opacity:1, scale:1}} className="glass p-10 max-w-xl w-full text-center">
          <Link to={`/groups/${groupId}`} className="text-primary-light hover:text-white mb-6 inline-block">← Back to Group</Link>
          <h1 className="text-3xl font-bold text-white mb-4">Import Expenses</h1>
          <p className="text-gray-400 mb-8">Upload your CSV file. Our smart engine will detect anomalies, missing data, and inconsistencies.</p>
          
          <div 
            className="border-2 border-dashed border-indigo-500/30 rounded-2xl p-12 mb-6 hover:border-primary-light transition cursor-pointer bg-indigo-500/5"
            onClick={() => fileInputRef.current?.click()}
          >
            <input type="file" ref={fileInputRef} onChange={handleFileChange} accept=".csv" className="hidden" />
            <div className="text-5xl mb-4">📄</div>
            <div className="text-lg font-medium text-white mb-1">
              {file ? file.name : 'Click to select CSV file'}
            </div>
            {!file && <div className="text-sm text-gray-500">Only .csv files are supported</div>}
          </div>

          {importError && <div className="text-red-400 mb-4">{importError}</div>}

          <button 
            onClick={handleUpload} 
            disabled={!file || uploading} 
            className="btn-primary w-full py-4 text-lg h-[60px] flex justify-center items-center"
          >
            {uploading ? <div className="spinner border-[2px] w-6 h-6 border-t-white" /> : 'Analyze File'}
          </button>
        </motion.div>
      </div>
    );
  }

  // Filter issues that need attention
  const pendingIssues = session.issues.filter(i => i.resolution === 'pending');
  const allResolved = pendingIssues.length === 0;

  return (
    <div className="min-h-screen pt-20 pb-20 px-4 sm:px-6 lg:px-8 max-w-6xl mx-auto">
      <div className="flex justify-between items-center mb-8">
        <div>
          <h1 className="text-3xl font-bold text-white mb-1">Review Anomalies</h1>
          <p className="text-gray-400">Found {session.issue_summary.total} issues in {session.total_rows} rows.</p>
        </div>
        <button 
          onClick={handleConfirmImport}
          disabled={!allResolved || confirming}
          className={`px-8 py-3 rounded-xl font-bold transition ${
            allResolved && !confirming
              ? 'bg-gradient-to-r from-green-500 to-emerald-600 text-white shadow-[0_0_20px_rgba(16,185,129,0.4)]'
              : 'bg-gray-800 text-gray-500 cursor-not-allowed'
          }`}
        >
          {confirming ? 'Importing...' : 'Confirm & Import'}
        </button>
      </div>

      {importError && (
        <div className="bg-red-500/10 border border-red-500/20 text-red-400 px-6 py-4 rounded-xl mb-8">
          {importError}
        </div>
      )}

      {allResolved ? (
        <motion.div initial={{opacity:0}} animate={{opacity:1}} className="glass border-green-500/30 p-12 text-center">
          <div className="text-6xl mb-4">✨</div>
          <h2 className="text-2xl font-bold text-white mb-2">All issues resolved!</h2>
          <p className="text-gray-400 mb-6">The data is clean and ready to be imported into your group.</p>
          <button onClick={handleConfirmImport} disabled={confirming} className="btn-success px-8 py-3 text-lg">
            {confirming ? 'Importing...' : 'Import Now'}
          </button>
        </motion.div>
      ) : (
        <div className="grid grid-cols-1 gap-6">
          <AnimatePresence>
            {pendingIssues.map(issue => (
              <motion.div 
                key={issue.id}
                initial={{opacity:0, y:20}} 
                animate={{opacity:1, y:0}}
                exit={{opacity:0, scale:0.95, transition:{duration:0.2}}}
                className={`glass p-6 border-l-4 ${
                  issue.severity === 'error' ? 'border-l-red-500' : 'border-l-yellow-500'
                }`}
              >
                <div className="flex justify-between items-start mb-4">
                  <div>
                    <span className={`badge mb-2 mr-2 ${issue.severity === 'error' ? 'badge-error' : 'badge-warning'}`}>
                      {issue.severity}
                    </span>
                    <span className="text-gray-400 text-sm">Row {issue.row_number}</span>
                    <h3 className="text-lg font-bold text-white mt-1">{issue.description}</h3>
                  </div>
                </div>

                <div className="bg-[#0f0d2e] rounded-lg p-4 mb-4 font-mono text-sm overflow-x-auto text-gray-300">
                  <span className="text-gray-500">Row context:</span> {issue.original_row_data.description || 'N/A'} | {issue.original_row_data.amount} {issue.original_row_data.currency} | Paid by: {issue.original_row_data.paid_by}
                </div>

                {activeIssue === issue.id ? (
                  <div className="flex items-center gap-3 mt-4">
                    <input 
                      type="text" 
                      value={customValue} 
                      onChange={e => setCustomValue(e.target.value)} 
                      placeholder="Enter custom value or instructions"
                      className="input-field flex-grow"
                    />
                    <button onClick={() => handleResolve(issue.id, 'modified', customValue)} className="btn-primary">Apply</button>
                    <button onClick={() => setActiveIssue(null)} className="btn-secondary">Cancel</button>
                  </div>
                ) : (
                  <div className="flex flex-wrap gap-3">
                    {issue.suggested_value && (
                      <button onClick={() => handleResolve(issue.id, 'accepted')} className="btn-success">
                        Accept Fix: {issue.suggested_value}
                      </button>
                    )}
                    <button onClick={() => handleResolve(issue.id, 'rejected')} className="btn-danger">
                      Reject / Skip Row
                    </button>
                    <button onClick={() => setActiveIssue(issue.id)} className="btn-secondary">
                      Modify Manually
                    </button>
                  </div>
                )}
              </motion.div>
            ))}
          </AnimatePresence>
        </div>
      )}
    </div>
  );
}
