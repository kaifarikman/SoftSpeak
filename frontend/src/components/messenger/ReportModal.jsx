import { useState, useEffect } from 'react';
import { API_URL } from '../../config';
import '../../css/components/ReportModal.css';

const REPORT_REASONS = [
  'оскорбление',
  'жесткое обращение с детьми',
  'насилие',
  'незаконные товары и услуги',
  'порнографические материалы',
  'мошенничество',
  'другое',
];

function ReportModal({ chatId, isOpen, onClose, onReportSubmitted }) {
  const [selectedReason, setSelectedReason] = useState('');
  const [description, setDescription] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    if (!isOpen) {
      setSelectedReason('');
      setDescription('');
      setError('');
    }
  }, [isOpen]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (!selectedReason) {
      setError('Выберите причину жалобы');
      return;
    }

    if (selectedReason === 'другое' && !description.trim()) {
      setError('Укажите описание для причины "другое"');
      return;
    }

    setLoading(true);
    setError('');

    try {
      const username = localStorage.getItem('username');
      if (!username) {
        setError('Пользователь не авторизован');
        setLoading(false);
        return;
      }

      const response = await fetch(`${API_URL}/reports?username=${username}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          chat_id: chatId,
          reason: selectedReason,
          description: selectedReason === 'другое' ? description.trim() : null,
        }),
      });

      const data = await response.json();

      if (response.ok && data.success) {
        if (onReportSubmitted) {
          onReportSubmitted(data.report);
        }
        onClose();
      } else {
        setError(data.detail || data.message || 'Ошибка отправки жалобы');
      }
    } catch (err) {
      setError('Ошибка отправки жалобы');
    } finally {
      setLoading(false);
    }
  };

  if (!isOpen) return null;

  return (
    <>
      <div className="report-modal-overlay" onClick={onClose} />
      <div className="report-modal">
        <div className="report-modal-header">
          <h2>Пожаловаться на пользователя</h2>
          <button className="report-modal-close" onClick={onClose}>×</button>
        </div>
        
        <form onSubmit={handleSubmit} className="report-modal-form">
          <div className="report-modal-content">
            <p className="report-modal-description">
              Выберите причину жалобы. Чат будет заблокирован до рассмотрения администратором.
            </p>

            <div className="report-reasons">
              {REPORT_REASONS.map((reason) => (
                <label key={reason} className="report-reason-item">
                  <input
                    type="radio"
                    name="reason"
                    value={reason}
                    checked={selectedReason === reason}
                    onChange={(e) => setSelectedReason(e.target.value)}
                  />
                  <span>{reason}</span>
                </label>
              ))}
            </div>

            {selectedReason === 'другое' && (
              <div className="report-description-field">
                <label>Опишите проблему</label>
                <textarea
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  placeholder="Опишите, что произошло..."
                  rows={4}
                  maxLength={500}
                />
                <span className="report-description-hint">
                  {description.length}/500 символов
                </span>
              </div>
            )}

            {error && (
              <div className="report-modal-error">
                {error}
              </div>
            )}
          </div>

          <div className="report-modal-footer">
            <button
              type="button"
              className="report-modal-cancel"
              onClick={onClose}
              disabled={loading}
            >
              Отмена
            </button>
            <button
              type="submit"
              className="report-modal-submit"
              disabled={loading || !selectedReason}
            >
              {loading ? 'Отправка...' : 'Пожаловаться'}
            </button>
          </div>
        </form>
      </div>
    </>
  );
}

export default ReportModal;

