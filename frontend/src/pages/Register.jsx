import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { useAuth } from '../context/AuthContext';

export default function Register() {
  const [formData, setFormData] = useState({
    username: '', email: '', first_name: '', password: '', password2: ''
  });
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();
  const { register, login } = useAuth();

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (formData.password !== formData.password2) {
      return setError('Passwords do not match');
    }
    setError('');
    setLoading(true);
    try {
      await register(formData);
      await login(formData.username, formData.password);
      navigate('/dashboard');
    } catch (err) {
      if (err.response?.data) {
        // DRF usually returns errors as objects or lists
        const data = err.response.data;
        if (typeof data === 'object') {
          const firstError = Object.values(data)[0];
          setError(Array.isArray(firstError) ? firstError[0] : firstError);
        } else {
          setError(data.detail || 'Registration failed');
        }
      } else {
        setError(err.message || 'Network Error - Check CORS or Server Status');
      }
    } finally {
      setLoading(false);
    }
  };

  const handleChange = (e) => {
    setFormData({ ...formData, [e.target.name]: e.target.value });
  };

  return (
    <div className="min-h-screen flex items-center justify-center hero-gradient px-4 py-12">
      <motion.div 
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="glass p-8 w-full max-w-md"
      >
        <div className="text-center mb-8">
          <Link to="/" className="text-2xl font-bold gradient-text inline-block mb-2">FairShare</Link>
          <h2 className="text-3xl font-bold text-white">Create an account</h2>
        </div>

        {error && (
          <div className="bg-red-500/10 border border-red-500/20 text-red-400 px-4 py-3 rounded-lg mb-6 text-sm text-center">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-1">Username</label>
            <input type="text" name="username" value={formData.username} onChange={handleChange} className="input-field" required />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-1">Email</label>
            <input type="email" name="email" value={formData.email} onChange={handleChange} className="input-field" required />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-1">First Name</label>
            <input type="text" name="first_name" value={formData.first_name} onChange={handleChange} className="input-field" required />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-1">Password</label>
            <input type="password" name="password" value={formData.password} onChange={handleChange} className="input-field" minLength={6} required />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-1">Confirm Password</label>
            <input type="password" name="password2" value={formData.password2} onChange={handleChange} className="input-field" minLength={6} required />
          </div>
          
          <button type="submit" className="btn-primary w-full py-3 mt-4 flex justify-center items-center h-[46px]" disabled={loading}>
            {loading ? <div className="spinner border-t-white w-5 h-5 border-[2px]" /> : 'Sign Up'}
          </button>
        </form>

        <div className="mt-6 text-center text-sm text-gray-400">
          Already have an account?{' '}
          <Link to="/login" className="text-primary-light hover:text-white transition font-medium">
            Sign in
          </Link>
        </div>
      </motion.div>
    </div>
  );
}
