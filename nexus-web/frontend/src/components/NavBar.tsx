import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import './NavBar.css';

export function NavBar() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate('/');
  };

  return (
    <nav className="navbar">
      <div className="navbar-brand">
        <Link to="/">Nexus</Link>
      </div>
      <div className="navbar-links">
        <Link to="/">Home</Link>
        <Link to="/play">Play</Link>
        <Link to="/rules">Rules</Link>
      </div>
      <div className="navbar-auth">
        {user ? (
          <>
            <span className="navbar-user">{user.username}</span>
            <button onClick={handleLogout} className="btn btn-secondary">Logout</button>
          </>
        ) : (
          <>
            <Link to="/login" className="btn btn-secondary">Login</Link>
            <Link to="/register" className="btn btn-primary">Register</Link>
          </>
        )}
      </div>
    </nav>
  );
}
