import { Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import { useAuth } from '../context/AuthContext';

export default function Home() {
  const { user } = useAuth();

  return (
    <div className="min-h-screen flex flex-col hero-gradient">
      {/* Navbar will be rendered by AppRoutes if user is logged in, 
          but let's add a public navbar for the landing page if not logged in */}
      {!user && (
        <nav className="fixed w-full top-0 z-50 px-6 py-4 flex justify-between items-center bg-transparent">
          <div className="text-2xl font-bold gradient-text">FairShare</div>
          <div className="space-x-4">
            <Link to="/login" className="text-gray-300 hover:text-white font-medium transition">Login</Link>
            <Link to="/register" className="btn-primary">Get Started</Link>
          </div>
        </nav>
      )}

      <main className="flex-grow flex items-center justify-center px-4 pt-20">
        <div className="max-w-5xl mx-auto text-center">
          <motion.h1 
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8 }}
            className="text-5xl md:text-7xl font-extrabold tracking-tight mb-6 text-white"
          >
            Shared expenses, <br/>
            <span className="gradient-text">made beautifully simple.</span>
          </motion.h1>
          
          <motion.p 
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8, delay: 0.2 }}
            className="text-lg md:text-xl text-gray-400 max-w-2xl mx-auto mb-10"
          >
            Track balances, handle multi-currency trips, and optimize settlements. 
            Import your messy spreadsheets and let our anomaly detector clean it up.
          </motion.p>
          
          <motion.div 
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ duration: 0.5, delay: 0.4 }}
            className="flex flex-col sm:flex-row items-center justify-center space-y-4 sm:space-y-0 sm:space-x-4"
          >
            <Link to={user ? "/dashboard" : "/register"} className="btn-primary py-3 px-8 text-lg w-full sm:w-auto">
              {user ? "Go to Dashboard" : "Start Splitting"}
            </Link>
            <a href="#features" className="btn-secondary py-3 px-8 text-lg w-full sm:w-auto">
              See How It Works
            </a>
          </motion.div>
        </div>
      </main>

      {/* Features Section */}
      <section id="features" className="py-20 bg-opacity-50 bg-[#0f0d2e]">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            <FeatureCard 
              title="Smart CSV Import" 
              desc="Our engine detects duplicates, missing data, and inconsistencies automatically."
              icon="📊"
            />
            <FeatureCard 
              title="Optimized Settlements" 
              desc="Minimize transactions. One number per person. Who pays whom, done."
              icon="💸"
            />
            <FeatureCard 
              title="Time-based Groups" 
              desc="Members join and leave? No problem. Balances adapt perfectly to timeframes."
              icon="⏳"
            />
          </div>
        </div>
      </section>
    </div>
  );
}

function FeatureCard({ title, desc, icon }) {
  return (
    <motion.div 
      whileHover={{ y: -5 }}
      className="glass p-6 text-center"
    >
      <div className="text-4xl mb-4 float-animation">{icon}</div>
      <h3 className="text-xl font-bold text-white mb-2">{title}</h3>
      <p className="text-gray-400">{desc}</p>
    </motion.div>
  );
}
