import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { AuthProvider } from './context/AuthContext';
import { NavBar } from './components';
import { HomePage, LoginPage, RegisterPage, PlayPage, GamePage, RulesPage } from './pages';
import './App.css';

function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <div className="app">
          <NavBar />
          <main className="app-content">
            <Routes>
              <Route path="/" element={<HomePage />} />
              <Route path="/login" element={<LoginPage />} />
              <Route path="/register" element={<RegisterPage />} />
              <Route path="/play" element={<PlayPage />} />
              <Route path="/game/:gameId" element={<GamePage />} />
              <Route path="/rules" element={<RulesPage />} />
            </Routes>
          </main>
        </div>
      </AuthProvider>
    </BrowserRouter>
  );
}

export default App;
