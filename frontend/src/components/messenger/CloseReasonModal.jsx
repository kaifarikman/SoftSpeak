import '../../css/components/CloseReasonModal.css';

const REASONS = [
  { id: 'connected', label: 'Нашли общий язык', emoji: '🤝' },
  { id: 'boring', label: 'Неинтересно', emoji: '😐' },
  { id: 'technical', label: 'Технические проблемы', emoji: '⚙️' },
  { id: 'other', label: 'Другое', emoji: '💬' },
];

function CloseReasonModal({ onConfirm, onCancel, loading = false, error = '' }) {
  return (
    <div className="close-reason-modal-backdrop" onClick={onCancel}>
      <div className="close-reason-modal" onClick={(event) => event.stopPropagation()}>
        <div className="close-reason-modal-header">
          <h2>Почему завершаете чат?</h2>
          <button className="close-reason-modal-close" onClick={onCancel} type="button">
            ×
          </button>
        </div>

        <div className="close-reason-modal-content">
          <p className="close-reason-modal-description">
            Это поможет нам улучшить анонимные чаты.
          </p>

          <div className="close-reason-list">
            {REASONS.map((reason) => (
              <button
                key={reason.id}
                className="close-reason-item"
                onClick={() => onConfirm(reason.id)}
                disabled={loading}
                type="button"
              >
                <span className="close-reason-emoji">{reason.emoji}</span>
                <span className="close-reason-label">{reason.label}</span>
              </button>
            ))}
          </div>

          {error && <div className="close-reason-error">{error}</div>}
        </div>

        <div className="close-reason-modal-footer">
          <button className="close-reason-cancel" onClick={onCancel} disabled={loading} type="button">
            Отмена
          </button>
        </div>
      </div>
    </div>
  );
}

export default CloseReasonModal;
