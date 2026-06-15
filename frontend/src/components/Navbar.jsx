import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

export default function Navbar() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate('/');
  };

  return (
    <nav className="glass fixed w-full top-0 z-50 rounded-none border-t-0 border-l-0 border-r-0">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          <div className="flex-shrink-0">
            <Link to={user ? '/dashboard' : '/'} className="text-2xl font-bold gradient-text">
              FairShare
            </Link>
          </div>
          <div className="flex items-center space-x-4">
            {user ? (
              <>
                <Link to="/dashboard" className="text-gray-300 hover:text-white transition">
                  Dashboard
                </Link>
                <div className="flex items-center space-x-2 ml-4">
                  <div className="h-8 w-8 rounded-full bg-primary flex items-center justify-center font-bold text-white shadow-[0_0_10px_rgba(99,102,241,0.5)]">
                    {user.first_name?.[0] || user.username[0].toUpperCase()}
                  </div>
                  <button onClick={handleLogout} className="text-sm text-gray-400 hover:text-white transition ml-2">
                    Logout
                  </button>
                </div>
              </>
            ) : (
              <>
                <Link to="/login" className="text-gray-300 hover:text-white transition font-medium">
                  Login
                </Link>
                <Link to="/register" className="btn-primary">
                  Sign Up
                </Link>
              </>
            )}
          </div>
        </div>
      </div>
    </nav>
  );
}
