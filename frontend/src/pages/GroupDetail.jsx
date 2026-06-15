import { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import api from '../api/axios';
import { useAuth } from '../context/AuthContext';

export default function GroupDetail() {
  const { groupId } = useParams();
  const { user } = useAuth();
  const [group, setGroup] = useState(null);
  const [balances, setBalances] = useState(null);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState('balances');

  useEffect(() => {
    fetchGroupData();
  }, [groupId]);

  const fetchGroupData = async () => {
    try {
      const [groupRes, balRes] = await Promise.all([
        api.get(`/groups/${groupId}/`),
        api.get(`/expenses/group/${groupId}/balances/`)
      ]);
      setGroup(groupRes.data);
      setBalances(balRes.data);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  if (loading) return <div className="min-h-screen pt-20 flex justify-center"><div className="spinner" /></div>;
  if (!group) return <div className="pt-20 text-center">Group not found</div>;

  return (
    <div className="min-h-screen pt-20 pb-10 px-4 sm:px-6 lg:px-8 max-w-7xl mx-auto">
      <div className="glass p-6 mb-8 flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
        <div>
          <h1 className="text-3xl font-bold text-white">{group.name}</h1>
          <p className="text-gray-400 mt-1">{group.description}</p>
        </div>
        <div className="flex gap-3">
          <Link to={`/groups/${groupId}/import`} className="btn-secondary">
            <span className="mr-2">📥</span> Import CSV
          </Link>
          <button className="btn-primary">+ Add Expense</button>
        </div>
      </div>

      <div className="flex space-x-1 mb-6 border-b border-indigo-500/20 overflow-x-auto">
        {['balances', 'expenses', 'settlements', 'members'].map(tab => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={`px-4 py-3 text-sm font-medium capitalize border-b-2 whitespace-nowrap transition-colors ${
              activeTab === tab ? 'border-primary text-white' : 'border-transparent text-gray-400 hover:text-gray-200'
            }`}
          >
            {tab}
          </button>
        ))}
      </div>

      {activeTab === 'balances' && balances && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          <div className="lg:col-span-2 space-y-6">
            <h2 className="text-xl font-bold text-white mb-4">Who owes whom (Optimized)</h2>
            {balances.settlements_needed.length === 0 ? (
              <div className="glass-light p-8 text-center text-gray-400">All settled up! 🎉</div>
            ) : (
              <div className="space-y-4">
                {balances.settlements_needed.map((s, i) => (
                  <motion.div initial={{opacity:0, y:10}} animate={{opacity:1, y:0}} transition={{delay:i*0.1}} key={i} className="glass p-4 flex justify-between items-center">
                    <div className="flex items-center gap-3">
                      <span className="font-semibold text-white">{s.from_user.first_name || s.from_user.username}</span>
                      <span className="text-gray-500">owes</span>
                      <span className="font-semibold text-white">{s.to_user.first_name || s.to_user.username}</span>
                    </div>
                    <div className="text-lg font-bold text-red-400">
                      {balances.currency} {s.amount}
                    </div>
                  </motion.div>
                ))}
              </div>
            )}
          </div>
          
          <div className="space-y-6">
            <h2 className="text-xl font-bold text-white mb-4">My Balance Breakdown</h2>
            <div className="glass p-6">
              <div className="mb-4">
                <span className="text-gray-400 text-sm">Total Paid</span>
                <div className="text-2xl font-bold text-green-400">{balances.currency} {balances.per_user_breakdown[user.id]?.total_paid || '0.00'}</div>
              </div>
              <div className="mb-4">
                <span className="text-gray-400 text-sm">Total Share</span>
                <div className="text-2xl font-bold text-red-400">{balances.currency} {balances.per_user_breakdown[user.id]?.total_owed || '0.00'}</div>
              </div>
              <div className="pt-4 border-t border-indigo-500/20">
                <span className="text-gray-400 text-sm">Net Balance</span>
                <div className={`text-3xl font-bold ${Number(balances.per_user_breakdown[user.id]?.net) >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                  {balances.currency} {Math.abs(Number(balances.per_user_breakdown[user.id]?.net || 0)).toFixed(2)}
                  <span className="text-sm font-normal text-gray-400 ml-2">
                    {Number(balances.per_user_breakdown[user.id]?.net) >= 0 ? 'owed to you' : 'you owe'}
                  </span>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {activeTab === 'members' && (
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-4">
          {group.members.map(m => (
            <div key={m.id} className="glass p-4 flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="h-10 w-10 rounded-full bg-primary/20 flex items-center justify-center font-bold text-primary-light">
                  {m.user.first_name?.[0] || m.user.username[0].toUpperCase()}
                </div>
                <div>
                  <div className="font-semibold text-white">{m.user.first_name || m.user.username}</div>
                  <div className="text-xs text-gray-400">Joined: {m.joined_at}</div>
                </div>
              </div>
              {!m.is_active && <span className="badge badge-warning">Left</span>}
            </div>
          ))}
        </div>
      )}

      {(activeTab === 'expenses' || activeTab === 'settlements') && (
        <div className="glass-light p-10 text-center text-gray-400">
          Content for {activeTab} goes here. <br/>(Due to time limits, focusing on the core import flow.)
        </div>
      )}
    </div>
  );
}
