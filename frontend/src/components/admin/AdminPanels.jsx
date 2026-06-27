export function AdminLoginPanel({
  loginForm,
  loginStatus,
  loading,
  onLogin,
  onLoginFormChange,
}) {
  return (
    <div className="admin-layout">
      <div className="admin-login-container">
        <form className="admin-card admin-login" onSubmit={onLogin}>
          <h1>Админка SoftSpeak</h1>
          <p>Введите данные, выданные разработчиками.</p>
          {loginStatus.message && (
            <div className={`admin-alert ${loginStatus.type}`}>{loginStatus.message}</div>
          )}
          <label>
            Имя
            <input
              type="text"
              value={loginForm.username}
              onChange={(e) => onLoginFormChange((prev) => ({ ...prev, username: e.target.value }))}
            />
          </label>
          <label>
            Пароль
            <input
              type="password"
              value={loginForm.password}
              onChange={(e) => onLoginFormChange((prev) => ({ ...prev, password: e.target.value }))}
            />
          </label>
          <button type="submit" className="admin-btn primary" disabled={loading}>
            {loading ? 'Входим...' : 'Войти'}
          </button>
        </form>
      </div>
    </div>
  );
}

export function StatsPanel({ stats }) {
  return (
    <section className="admin-section stats-grid">
      <div className="stat-card">
        <strong>{stats.categories}</strong>
        <span>Категорий</span>
      </div>
      <div className="stat-card">
        <strong>{stats.questions}</strong>
        <span>Всего вопросов</span>
      </div>
      <div className="stat-card">
        <strong>{stats.activeQuestions}</strong>
        <span>Активных</span>
      </div>
      <div className="stat-card">
        <strong>{stats.adjectives}/{stats.nouns}</strong>
        <span>Прилаг./ сущ.</span>
      </div>
    </section>
  );
}

export function QuestionsPanel({
  categories,
  questionsByCategory,
  questionForm,
  loading,
  onQuestionFormChange,
  onAddQuestion,
  onToggleQuestion,
  onDeleteQuestion,
}) {
  return (
    <>
      <section className="admin-section">
        <h2>Добавить вопрос</h2>
        <form className="question-form" onSubmit={onAddQuestion}>
          <label>
            Категория
            <select
              value={questionForm.categoryId}
              onChange={(e) => onQuestionFormChange((prev) => ({ ...prev, categoryId: e.target.value }))}
            >
              {categories.map((cat) => (
                <option key={cat.id} value={cat.id}>
                  {cat.name}
                </option>
              ))}
            </select>
          </label>
          <label>
            Текст вопроса
            <textarea
              value={questionForm.text}
              onChange={(e) => onQuestionFormChange((prev) => ({ ...prev, text: e.target.value }))}
            />
          </label>
          <label>
            Порядок
            <input
              type="number"
              value={questionForm.order}
              onChange={(e) => onQuestionFormChange((prev) => ({ ...prev, order: e.target.value }))}
            />
          </label>
          <button className="admin-btn primary" type="submit" disabled={loading}>
            Добавить
          </button>
        </form>
      </section>

      <section className="admin-section">
        <div className="section-header">
          <h2>Категории и вопросы</h2>
        </div>
        <div className="categories-grid">
          {categories.map((cat) => (
            <div className="category-card" key={cat.id}>
              <div className="category-head">
                <div>
                  <strong>{cat.name}</strong>
                  <p>{cat.description || 'Без описания'}</p>
                </div>
                <span className="badge">{questionsByCategory[cat.id]?.length || 0} вопросов</span>
              </div>
              <div className="question-list">
                {(questionsByCategory[cat.id] || []).map((q) => (
                  <div key={q.id} className={`question-item ${q.is_active ? '' : 'inactive'}`}>
                    <div>
                      <p>{q.text}</p>
                      <span>Порядок: {q.order} • {q.is_active ? 'Активен' : 'Скрыт'}</span>
                    </div>
                    <div className="question-actions">
                      <button
                        className="admin-btn ghost"
                        type="button"
                        onClick={() => onToggleQuestion(q.id, !q.is_active)}
                      >
                        {q.is_active ? 'Скрыть' : 'Показать'}
                      </button>
                      <button
                        className="admin-btn danger"
                        type="button"
                        onClick={() => onDeleteQuestion(q.id)}
                      >
                        Удалить
                      </button>
                    </div>
                  </div>
                ))}
                {(questionsByCategory[cat.id] || []).length === 0 && (
                  <p className="empty-placeholder">Нет вопросов</p>
                )}
              </div>
            </div>
          ))}
        </div>
      </section>
    </>
  );
}

export function NamesPanel({
  words,
  wordForms,
  onWordFormsChange,
  onAddWord,
  onToggleWord,
  onDeleteWord,
}) {
  return (
    <section className="admin-section">
      <div className="section-header">
        <h2>Псевдонимы для анонимных чатов</h2>
      </div>
      <div className="words-grid">
        {['adjective', 'noun'].map((type) => {
          const list = words[type === 'adjective' ? 'adjectives' : 'nouns'];
          const title = type === 'adjective' ? 'Прилагательные' : 'Существительные';
          return (
            <div key={type} className="word-card">
              <div className="word-card-head">
                <h3>{title}</h3>
                <span className="badge">{list.length}</span>
              </div>
              <div className="word-add-row">
                <input
                  type="text"
                  placeholder={`Новое ${title.toLowerCase()}`}
                  value={wordForms[type]}
                  onChange={(e) =>
                    onWordFormsChange((prev) => ({ ...prev, [type]: e.target.value }))
                  }
                />
                <button
                  className="admin-btn primary"
                  type="button"
                  onClick={() => onAddWord(type)}
                >
                  Добавить
                </button>
              </div>
              <div className="word-list">
                {list.map((word) => (
                  <div key={word.id} className="word-item">
                    <span className={word.is_active ? '' : 'muted'}>{word.text}</span>
                    <div className="word-actions">
                      <button
                        className="admin-btn ghost"
                        type="button"
                        onClick={() =>
                          onToggleWord(type === 'adjective' ? 'adjectives' : 'nouns', word)
                        }
                      >
                        {word.is_active ? 'Выключить' : 'Включить'}
                      </button>
                      <button
                        className="admin-btn danger"
                        type="button"
                        onClick={() =>
                          onDeleteWord(type === 'adjective' ? 'adjectives' : 'nouns', word.id)
                        }
                      >
                        ×
                      </button>
                    </div>
                  </div>
                ))}
                {list.length === 0 && <p className="empty-placeholder">Пока пусто</p>}
              </div>
            </div>
          );
        })}
      </div>
    </section>
  );
}

export function ReportsPanel({
  reports,
  selectedReport,
  reportMessages,
  reportStatusFilter,
  bannedUsers,
  showBannedUsers,
  onStatusFilterChange,
  onShowBannedUsersChange,
  onSelectedReportChange,
  onReportMessagesChange,
  onViewReport,
  onBanUser,
  onRejectReport,
  onUnbanUser,
}) {
  return (
    <>
      <section className="admin-section">
        <div className="section-header">
          <h2>Жалобы пользователей</h2>
        </div>
        <div className="reports-container">
          <div className="reports-filter">
            <button
              className={`admin-btn ${reportStatusFilter === 'pending' ? 'primary' : 'ghost'}`}
              onClick={() => {
                onStatusFilterChange('pending');
                onShowBannedUsersChange(false);
              }}
            >
              Ожидают ({reports.filter(r => r.status === 'pending').length})
            </button>
            <button
              className={`admin-btn ${reportStatusFilter === '' ? 'primary' : 'ghost'}`}
              onClick={() => {
                onStatusFilterChange('');
                onShowBannedUsersChange(false);
              }}
            >
              Все ({reports.length})
            </button>
            <button
              className={`admin-btn ${showBannedUsers ? 'primary' : 'ghost'}`}
              onClick={() => {
                onShowBannedUsersChange(true);
                onStatusFilterChange('');
                onSelectedReportChange(null);
              }}
            >
              Забаненные ({bannedUsers.length})
            </button>
          </div>
          <div className="reports-list">
            {showBannedUsers ? (
              bannedUsers.length === 0 ? (
                <p className="empty-placeholder">Нет забаненных пользователей</p>
              ) : (
                bannedUsers.map((user) => (
                  <div key={user.id} className="report-item">
                    <div className="report-header">
                      <span className="report-reason">{user.nickname}</span>
                      <span className="report-status banned">Забанен</span>
                    </div>
                    <div className="report-info">
                      <span>Email: {user.email}</span>
                      <span>ID: {user.id}</span>
                    </div>
                    <div className="report-actions" style={{ marginTop: '10px' }}>
                      <button
                        className="admin-btn primary"
                        onClick={() => onUnbanUser(user.id)}
                      >
                        Разблокировать
                      </button>
                    </div>
                  </div>
                ))
              )
            ) : reports.length === 0 ? (
              <p className="empty-placeholder">Нет жалоб</p>
            ) : (
              reports.map((report) => (
                <div
                  key={report.id}
                  className={`report-item ${selectedReport?.id === report.id ? 'active' : ''}`}
                  onClick={() => onViewReport(report)}
                >
                  <div className="report-header">
                    <span className="report-reason">{report.reason}</span>
                    <span className={`report-status ${report.status}`}>{report.status}</span>
                  </div>
                  <div className="report-info">
                    <span>От: {report.reporter_username || report.reporter_id}</span>
                    <span>На: {report.reported_user_username || report.reported_user_id}</span>
                  </div>
                  {report.description && (
                    <div className="report-description">{report.description}</div>
                  )}
                  <div className="report-date">
                    {new Date(report.created_at).toLocaleString('ru-RU')}
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      </section>

      {selectedReport && (
        <section className="admin-section report-details">
          <div className="section-header">
            <h2>Детали жалобы #{selectedReport.id}</h2>
            <button
              className="admin-btn ghost"
              onClick={() => {
                onSelectedReportChange(null);
                onReportMessagesChange([]);
              }}
            >
              Закрыть
            </button>
          </div>
          <div className="report-detail-info">
            <div><strong>Причина:</strong> {selectedReport.reason}</div>
            <div><strong>От:</strong> {selectedReport.reporter_username || selectedReport.reporter_id}</div>
            <div><strong>На:</strong> {selectedReport.reported_user_username || selectedReport.reported_user_id}</div>
            {selectedReport.description && (
              <div><strong>Описание:</strong> {selectedReport.description}</div>
            )}
            <div><strong>Дата:</strong> {new Date(selectedReport.created_at).toLocaleString('ru-RU')}</div>
          </div>
          <div className="report-messages">
            <h3>Сообщения в чате</h3>
            {reportMessages.length === 0 ? (
              <p className="empty-placeholder">Сообщений нет</p>
            ) : (
              <div className="messages-list">
                {reportMessages.map((msg) => (
                  <div key={msg.id} className="message-item">
                    <div className="message-header">
                      <span>ID: {msg.sender_id}</span>
                      <span>{new Date(msg.created_at).toLocaleString('ru-RU')}</span>
                    </div>
                    <div className="message-content">{msg.content}</div>
                  </div>
                ))}
              </div>
            )}
          </div>
          {selectedReport.status === 'pending' && (
            <div className="report-actions">
              <button
                className="admin-btn danger"
                onClick={() => onBanUser(selectedReport.id)}
              >
                Забанить пользователя
              </button>
              <button
                className="admin-btn primary"
                onClick={() => onRejectReport(selectedReport.id)}
              >
                Отклонить жалобу
              </button>
            </div>
          )}
        </section>
      )}
    </>
  );
}
