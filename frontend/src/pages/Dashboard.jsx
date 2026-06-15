import { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import api from '../api/axios';

export default function Dashboard() {
  const [groups, setGroups] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);
  const [newGroup, setNewGroup] = useState({ name: '', description: '', default_currency: 'INR' });
  const navigate = useNavigate();

  useEffect(() => {
    fetchGroups();
  }, []);

  const fetchGroups = async () => {
    try {
      const res = await api.get('/groups/');
      setGroups(res.data.results || res.data);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleCreate = async (e) => {
    e.preventDefault();
    try {
      const res = await api.post('/groups/', newGroup);
      setGroups([res.data, ...groups]);
      setShowCreate(false);
      setNewGroup({ name: '', description: '', default_currency: 'INR' });
    } catch (err) {
      console.error(err);
    }
  };

  if (loading) return <div className="min-h-screen pt-20 flex justify-center"><div className="spinner" /></div>;

  return (
    <div className="min-h-screen pt-20 pb-10 px-4 sm:px-6 lg:px-8 max-w-7xl mx-auto">
      <div className="flex justify-between items-center mb-8">
        <div>
          <h1 className="text-3xl font-bold text-white">Your Groups</h1>
          <p className="text-gray-400 mt-1">Manage your shared expenses</p>
        </div>
        <button onClick={() => setShowCreate(!showCreate)} className="btn-primary">
          {showCreate ? 'Cancel' : '+ New Group'}
        </button>
      </div>

      {showCreate && (
        <motion.div initial={{ opacity: 0, y: -20 }} animate={{ opacity: 1, y: 0 }} className="glass-light p-6 mb-8 max-w-2xl">
          <h2 className="text-xl font-bold text-white mb-4">Create a New Group</h2>
          <form onSubmit={handleCreate} className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-1">Group Name</label>
              <input type="text" value={newGroup.name} onChange={e => setNewGroup({...newGroup, name: e.target.value})} className="input-field" required />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-1">Description (optional)</label>
              <input type="text" value={newGroup.description} onChange={e => setNewGroup({...newGroup, description: e.target.value})} className="input-field" />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-1">Default Currency</label>
              <select value={newGroup.default_currency} onChange={e => setNewGroup({...newGroup, default_currency: e.target.value})} className="input-field">
                <option value="INR">INR (₹)</option>
                <option value="USD">USD ($)</option>
              </select>
            </div>
            <button type="submit" className="btn-primary">Create Group</button>
          </form>
        </motion.div>
      )}

      {groups.length === 0 && !showCreate ? (
        <div className="text-center py-20 glass rounded-2xl">
          <div className="text-6xl mb-4">🏠</div>
          <h3 className="text-2xl font-bold text-white mb-2">No groups yet</h3>
          <p className="text-gray-400 mb-6">Create a group to start tracking expenses with your flatmates or friends.</p>
          <button onClick={() => setShowCreate(true)} className="btn-primary py-2 px-6">Create First Group</button>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {groups.map(group => (
            <motion.div whileHover={{ y: -4 }} key={group.id} className="glass p-6 flex flex-col h-full cursor-pointer" onClick={() => navigate(`/groups/${group.id}`)}>
              <div className="flex-grow">
                <div className="flex justify-between items-start mb-4">
                  <h3 className="text-xl font-bold text-white line-clamp-1">{group.name}</h3>
                  <span className="badge badge-info">{group.default_currency}</span>
                </div>
                {group.description && <p className="text-gray-400 text-sm mb-4 line-clamp-2">{group.description}</p>}
              </div>
              <div className="mt-4 pt-4 border-t border-indigo-500/20 flex justify-between items-center text-sm">
                <span className="text-gray-400">{group.member_count} members</span>
                <span className="text-primary-light group-hover:text-white transition">View Details →</span>
              </div>
            </motion.div>
          ))}
        </div>
      )}
    </div>
  );
}
