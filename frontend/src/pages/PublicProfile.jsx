import { useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { API_URL } from '../config';

function PublicProfile() {
  const { nickname } = useParams();
  const navigate = useNavigate();
  const [profile, setProfile] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    if (!nickname) {
      setError('Профиль не найден');
      setLoading(false);
      return;
    }

    fetch(`${API_URL}/settings/profile/by-nickname/${encodeURIComponent(nickname)}`)
      .then(async (response) => {
        if (!response.ok) {
          throw new Error('Профиль не найден');
        }
        return response.json();
      })
      .then(setProfile)
      .catch((err) => setError(err.message || 'Не удалось загрузить профиль'))
      .finally(() => setLoading(false));
  }, [nickname]);

  if (loading) {
    return (
      <div className="container">
        <div className="form-box">
          <p className="subtitle">Загрузка...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="container">
      <div className="form-box">
        {error ? (
          <>
            <h1>Профиль</h1>
            <p className="error-text">{error}</p>
          </>
        ) : (
          <>
            <h1>{profile.nickname}</h1>
            <p className="subtitle">{profile.bio || 'Пользователь пока ничего не рассказал о себе.'}</p>
          </>
        )}
        <button type="button" className="btn" onClick={() => navigate('/')}>
          На главную
        </button>
      </div>
    </div>
  );
}

export default PublicProfile;
