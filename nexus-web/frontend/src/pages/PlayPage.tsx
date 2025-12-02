import { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { Seek, GameListItem } from '../types';
import {
  createSeek,
  getSeeks,
  getMySeek,
  cancelSeek,
  acceptSeek,
  getMyGames,
} from '../api/client';
import './PlayPage.css';

export function PlayPage() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [seeks, setSeeks] = useState<Seek[]>([]);
  const [mySeek, setMySeek] = useState<Seek | null>(null);
  const [myGames, setMyGames] = useState<GameListItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedSize, setSelectedSize] = useState(5);
  const [selectedMode, setSelectedMode] = useState<'realtime' | 'correspondence'>('realtime');

  const refreshData = useCallback(async () => {
    if (!user) return;
    try {
      const [seeksData, mySeekData, gamesData] = await Promise.all([
        getSeeks(),
        getMySeek(),
        getMyGames(),
      ]);
      setSeeks(seeksData);
      setMySeek(mySeekData);
      setMyGames(gamesData);
    } catch (err) {
      console.error('Failed to refresh data:', err);
    }
  }, [user]);

  useEffect(() => {
    refreshData();
    // Poll for updates every 5 seconds
    const interval = setInterval(refreshData, 5000);
    return () => clearInterval(interval);
  }, [refreshData]);

  const handleCreateSeek = async () => {
    if (!user) {
      navigate('/login');
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const seek = await createSeek(selectedMode, selectedSize);
      setMySeek(seek);
      await refreshData();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create seek');
    } finally {
      setLoading(false);
    }
  };

  const handleCancelSeek = async () => {
    if (!mySeek) return;
    setLoading(true);
    try {
      await cancelSeek(mySeek.id);
      setMySeek(null);
      await refreshData();
    } catch (err) {
      // If the seek wasn't found, it may have been matched - check for new games
      const [mySeekData, gamesData] = await Promise.all([getMySeek(), getMyGames()]);
      setMySeek(mySeekData);
      setMyGames(gamesData);

      if (!mySeekData) {
        // Seek was matched, check if there's a new ongoing game to navigate to
        const ongoingGames = gamesData.filter(g => g.result === 'ongoing');
        if (ongoingGames.length > 0) {
          // Navigate to the most recent game (likely the one from this seek)
          navigate(`/game/${ongoingGames[0].id}`);
          return;
        }
      }
      setError(err instanceof Error ? err.message : 'Failed to cancel seek');
    } finally {
      setLoading(false);
    }
  };

  const handleAcceptSeek = async (seekId: number) => {
    if (!user) {
      navigate('/login');
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const game = await acceptSeek(seekId);
      navigate(`/game/${game.game_id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to accept seek');
    } finally {
      setLoading(false);
    }
  };

  if (!user) {
    return (
      <div className="play-page">
        <div className="login-prompt">
          <h2>Sign in to Play</h2>
          <p>You need an account to play online games.</p>
          <button onClick={() => navigate('/login')} className="btn btn-primary btn-large">
            Sign In
          </button>
          <button onClick={() => navigate('/register')} className="btn btn-secondary btn-large">
            Create Account
          </button>
        </div>
      </div>
    );
  }

  const ongoingGames = myGames.filter(g => g.result === 'ongoing');
  const finishedGames = myGames.filter(g => g.result !== 'ongoing');

  return (
    <div className="play-page">
      <div className="play-content">
        <section className="create-game-section">
          <h2>Create a Game</h2>
          {mySeek ? (
            <div className="my-seek">
              <p>
                Waiting for opponent...
                <br />
                <span className="seek-details">
                  {mySeek.mode} | {mySeek.board_size}x{mySeek.board_size}
                </span>
              </p>
              <button onClick={handleCancelSeek} className="btn btn-secondary" disabled={loading}>
                Cancel
              </button>
            </div>
          ) : (
            <div className="create-game-form">
              <div className="form-row">
                <label>Board Size</label>
                <div className="button-group">
                  {[3, 5, 7].map(size => (
                    <button
                      key={size}
                      className={`btn ${selectedSize === size ? 'btn-primary' : 'btn-secondary'}`}
                      onClick={() => setSelectedSize(size)}
                    >
                      {size}x{size}
                    </button>
                  ))}
                </div>
              </div>
              <div className="form-row">
                <label>Mode</label>
                <div className="button-group">
                  <button
                    className={`btn ${selectedMode === 'realtime' ? 'btn-primary' : 'btn-secondary'}`}
                    onClick={() => setSelectedMode('realtime')}
                  >
                    Real-time
                  </button>
                  <button
                    className={`btn ${selectedMode === 'correspondence' ? 'btn-primary' : 'btn-secondary'}`}
                    onClick={() => setSelectedMode('correspondence')}
                  >
                    Correspondence
                  </button>
                </div>
              </div>
              <button
                onClick={handleCreateSeek}
                className="btn btn-primary btn-large"
                disabled={loading}
              >
                {loading ? 'Creating...' : 'Find Opponent'}
              </button>
            </div>
          )}
          {error && <div className="error-message">{error}</div>}
        </section>

        <section className="seeks-section">
          <h2>Open Games</h2>
          {seeks.length === 0 ? (
            <p className="empty-message">No open games. Create one above!</p>
          ) : (
            <div className="seeks-list">
              {seeks.map(seek => (
                <div key={seek.id} className="seek-item">
                  <div className="seek-info">
                    <strong>{seek.owner_username}</strong>
                    <span className="seek-details">
                      {seek.mode} | {seek.board_size}x{seek.board_size}
                    </span>
                  </div>
                  <button
                    onClick={() => handleAcceptSeek(seek.id)}
                    className="btn btn-primary"
                    disabled={loading}
                  >
                    Join
                  </button>
                </div>
              ))}
            </div>
          )}
        </section>

        <section className="games-section">
          <h2>Your Games</h2>
          {ongoingGames.length === 0 && finishedGames.length === 0 ? (
            <p className="empty-message">No games yet. Start playing!</p>
          ) : (
            <>
              {ongoingGames.length > 0 && (
                <div className="games-group">
                  <h3>Ongoing</h3>
                  <div className="games-list">
                    {ongoingGames.map(game => (
                      <div
                        key={game.id}
                        className="game-item"
                        onClick={() => navigate(`/game/${game.id}`)}
                      >
                        <div className="game-players">
                          <span className={game.player_black_id === user.id ? 'you' : ''}>
                            {game.player_black_username || 'Waiting...'}
                          </span>
                          <span className="vs">vs</span>
                          <span className={game.player_white_id === user.id ? 'you' : ''}>
                            {game.player_white_username || 'Waiting...'}
                          </span>
                        </div>
                        <div className="game-info">
                          <span>{game.board_size}x{game.board_size}</span>
                          <span>{game.mode}</span>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
              {finishedGames.length > 0 && (
                <div className="games-group">
                  <h3>Finished</h3>
                  <div className="games-list">
                    {finishedGames.slice(0, 10).map(game => (
                      <div
                        key={game.id}
                        className="game-item finished"
                        onClick={() => navigate(`/game/${game.id}`)}
                      >
                        <div className="game-players">
                          <span className={game.player_black_id === user.id ? 'you' : ''}>
                            {game.player_black_username}
                          </span>
                          <span className="vs">vs</span>
                          <span className={game.player_white_id === user.id ? 'you' : ''}>
                            {game.player_white_username}
                          </span>
                        </div>
                        <div className="game-result">
                          {game.result === 'black_win' ? 'Black wins' : 'White wins'}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </>
          )}
        </section>
      </div>
    </div>
  );
}
