import { useEffect, useState } from 'react';
import { API_URL } from '../../config';
import { apiFetch } from '../../utils/apiHelper';
import '../../css/components/CompatibilityModal.css';

function CompatibilityModal({ chatId, email, onClose }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    let isMounted = true;

    const loadCompatibility = async () => {
      if (!chatId || !email) {
        setError('Не удалось загрузить данные совместимости');
        setLoading(false);
        return;
      }

      setLoading(true);
      setError('');

      try {
        const response = await apiFetch(
          `${API_URL}/matchmaking/chat/${chatId}/compatibility?email=${encodeURIComponent(email)}`
        );
        if (!response.ok) {
          let message = 'Не удалось загрузить данные совместимости';
          try {
            const payload = await response.json();
            message = payload.detail || payload.message || message;
          } catch (parseError) {
            message = response.status === 404 ? 'Чат не найден' : message;
          }
          throw new Error(message);
        }

        const payload = await response.json();
        if (isMounted) {
          setData(payload);
        }
      } catch (err) {
        if (isMounted) {
          setError(err.message || 'Не удалось загрузить данные совместимости');
        }
      } finally {
        if (isMounted) {
          setLoading(false);
        }
      }
    };

    loadCompatibility();

    return () => {
      isMounted = false;
    };
  }, [chatId, email]);

  if (!chatId) {
    return null;
  }

  return (
    <div className="compatibility-modal-backdrop" onClick={onClose}>
      <div className="compatibility-modal" onClick={(event) => event.stopPropagation()}>
        <div className="compatibility-modal-header">
          <h2>Совместимость</h2>
          <button className="compatibility-modal-close" onClick={onClose} type="button">
            ×
          </button>
        </div>

        <div className="compatibility-modal-content">
          {loading && <p className="compatibility-modal-state">Загружаем совместимость...</p>}
          {!loading && error && <p className="compatibility-modal-error">{error}</p>}
          {!loading && !error && data && (
            <>
              <div className="compatibility-score">
                <span className="compatibility-score-value">{data.score}%</span>
                <span className="compatibility-score-label">совместимость</span>
              </div>

              {Array.isArray(data.common_tags) && data.common_tags.length > 0 && (
                <div className="compatibility-tags-block">
                  <p className="compatibility-section-title">Общие интересы</p>
                  <div className="compatibility-tag-list">
                    {data.common_tags.map((tag) => (
                      <span key={`${tag.name}-${tag.emoji}`} className="compatibility-tag">
                        <span className="compatibility-tag-emoji">{tag.emoji}</span>
                        <span>{tag.name}</span>
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </>
          )}
        </div>

        <div className="compatibility-modal-footer">
          <button className="compatibility-modal-button" onClick={onClose} type="button">
            Продолжить общение
          </button>
        </div>
      </div>
    </div>
  );
}

export default CompatibilityModal;
