import { useEffect, useMemo, useState } from 'react';
import '../css/Admin.css';
import { API_URL } from '../config';

const initialLogin = { username: 'admin', password: 'admin' };

function Admin() {
  const [token, setToken] = useState(() => localStorage.getItem('admin_token') || '');
  const [loginForm, setLoginForm] = useState(initialLogin);
  const [loginStatus, setLoginStatus] = useState({ type: '', message: '' });
  const [loading, setLoading] = useState(false);
  const [categories, setCategories] = useState([]);
  const [questionsByCategory, setQuestionsByCategory] = useState({});
  const [questionForm, setQuestionForm] = useState({ categoryId: '', order: 0, text: '' });
  const [words, setWords] = useState({ adjectives: [], nouns: [] });
  const [wordForms, setWordForms] = useState({ adjective: '', noun: '' });
  const [panelMessage, setPanelMessage] = useState({ type: '', message: '' });
  const [reports, setReports] = useState([]);
  const [selectedReport, setSelectedReport] = useState(null);
  const [reportMessages, setReportMessages] = useState([]);
  const [reportStatusFilter, setReportStatusFilter] = useState('pending');
  const [bannedUsers, setBannedUsers] = useState([]);
  const [showBannedUsers, setShowBannedUsers] = useState(false);


  useEffect(() => {
    document.documentElement.classList.add('admin-page');
    document.body.classList.add('admin-page');
    
    return () => {
      document.documentElement.classList.remove('admin-page');
      document.body.classList.remove('admin-page');
    };
  }, []);

  useEffect(() => {
    if (token) {
      loadAllData();
      loadReports();
      if (showBannedUsers) {
        loadBannedUsers();
      }
    }
  }, [token, reportStatusFilter, showBannedUsers]);

  const loadReports = async () => {
    try {
      const response = await authorizedFetch(`/admin/reports?status=${reportStatusFilter}`);
      if (response.ok) {
        const data = await response.json();
        setReports(data);
      }
    } catch (err) {
      console.error('Ошибка загрузки жалоб:', err);
    }
  };

  const loadReportMessages = async (reportId) => {
    try {
      const response = await authorizedFetch(`/admin/reports/${reportId}/chat`);
      if (response.ok) {
        const data = await response.json();
        setReportMessages(data.messages || []);
      }
    } catch (err) {
      console.error('Ошибка загрузки сообщений:', err);
      setReportMessages([]);
    }
  };

  const handleViewReport = async (report) => {
    setSelectedReport(report);
    await loadReportMessages(report.id);
  };

  const handleBanUser = async (reportId) => {
    if (!confirm('Забанить пользователя? Это действие нельзя отменить.')) {
      return;
    }
    try {
      const response = await authorizedFetch(`/admin/reports/${reportId}/ban`, {
        method: 'POST',
      });
      if (response.ok) {
        setPanelMessage({ type: 'success', message: 'Пользователь забанен' });
        loadReports();
        setSelectedReport(null);
        setReportMessages([]);
      } else {
        const data = await response.json();
        setPanelMessage({ type: 'error', message: data.detail || 'Ошибка' });
      }
    } catch (err) {
      setPanelMessage({ type: 'error', message: err.message });
    }
  };

  const loadBannedUsers = async () => {
    try {
      const response = await authorizedFetch('/admin/users/banned');
      if (response.ok) {
        const data = await response.json();
        setBannedUsers(data);
      }
    } catch (err) {
      console.error('Ошибка загрузки забаненных пользователей:', err);
    }
  };

  const handleUnbanUser = async (userId) => {
    if (!confirm('Разблокировать пользователя?')) {
      return;
    }
    try {
      const response = await authorizedFetch(`/admin/users/${userId}/unban`, {
        method: 'POST',
      });
      if (response.ok) {
        setPanelMessage({ type: 'success', message: 'Пользователь разблокирован' });
        loadBannedUsers();
      } else {
        const data = await response.json();
        setPanelMessage({ type: 'error', message: data.detail || 'Ошибка' });
      }
    } catch (err) {
      setPanelMessage({ type: 'error', message: err.message });
    }
  };

  const handleRejectReport = async (reportId) => {
    if (!confirm('Отклонить жалобу? Чат будет разблокирован.')) {
      return;
    }
    try {
      const response = await authorizedFetch(`/admin/reports/${reportId}/reject`, {
        method: 'POST',
      });
      if (response.ok) {
        setPanelMessage({ type: 'success', message: 'Жалоба отклонена' });
        loadReports();
        setSelectedReport(null);
        setReportMessages([]);
      } else {
        const data = await response.json();
        setPanelMessage({ type: 'error', message: data.detail || 'Ошибка' });
      }
    } catch (err) {
      setPanelMessage({ type: 'error', message: err.message });
    }
  };

  const authorizedFetch = async (path, options = {}) => {
    const headers = { ...(options.headers || {}) };
    if (options.body && !headers['Content-Type']) {
      headers['Content-Type'] = 'application/json';
    }
    const response = await fetch(`${API_URL}${path}`, {
      ...options,
      headers: {
        ...headers,
        Authorization: `Bearer ${token}`,
      },
    });

    if (response.status === 401) {
      handleLogout();
      throw new Error('Сессия истекла, войдите снова');
    }

    return response;
  };

  const handleLogin = async (e) => {
    e.preventDefault();
    setLoginStatus({ type: '', message: '' });
    setLoading(true);
    try {
      const response = await fetch(`${API_URL}/admin/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(loginForm),
      });
      
      let data;
      try {
        data = await response.json();
      } catch (parseError) {
        throw new Error(`Ошибка сервера: ${response.status} ${response.statusText}`);
      }
      
      if (!response.ok) {
        throw new Error(data?.detail || `Ошибка входа: ${response.status}`);
      }
      
      if (!data.token) {
        throw new Error('Токен не получен от сервера');
      }
      
      localStorage.setItem('admin_token', data.token);
      setToken(data.token);
      setLoginStatus({ type: 'success', message: 'Вход выполнен' });
    } catch (error) {
      console.error('Admin login error:', error);
      setLoginStatus({ type: 'error', message: error.message || 'Ошибка входа' });
    } finally {
      setLoading(false);
    }
  };

  const handleLogout = () => {
    localStorage.removeItem('admin_token');
    setToken('');
    setCategories([]);
    setQuestionsByCategory({});
    setWords({ adjectives: [], nouns: [] });
    setPanelMessage({ type: '', message: '' });
    setLoginForm(initialLogin);
  };

  const loadAllData = async () => {
    setLoading(true);
    try {
      const categoriesResponse = await authorizedFetch('/admin/categories');
      const categoriesData = await categoriesResponse.json();
      const questionsData = {};
      for (const category of categoriesData) {
        const res = await authorizedFetch(`/admin/categories/${category.id}/questions`);
        questionsData[category.id] = await res.json();
      }
      setCategories(categoriesData);
      setQuestionsByCategory(questionsData);
      if (!questionForm.categoryId && categoriesData.length > 0) {
        setQuestionForm((prev) => ({ ...prev, categoryId: categoriesData[0].id }));
      }
      await loadWords();
      setPanelMessage({ type: 'success', message: 'Данные обновлены' });
    } catch (error) {
      setPanelMessage({ type: 'error', message: error.message });
    } finally {
      setLoading(false);
    }
  };

  const loadWords = async () => {
    const [adjRes, nounRes] = await Promise.all([
      authorizedFetch('/admin/random-names/adjectives'),
      authorizedFetch('/admin/random-names/nouns'),
    ]);
    const adjectives = await adjRes.json();
    const nouns = await nounRes.json();
    setWords({ adjectives, nouns });
  };

  const stats = useMemo(() => {
    const allQuestions = Object.values(questionsByCategory).flat();
    return {
      categories: categories.length,
      questions: allQuestions.length,
      activeQuestions: allQuestions.filter((q) => q.is_active).length,
      adjectives: words.adjectives.length,
      nouns: words.nouns.length,
    };
  }, [categories, questionsByCategory, words]);

  const handleAddQuestion = async (e) => {
    e.preventDefault();
    if (!questionForm.text.trim()) {
      setPanelMessage({ type: 'error', message: 'Введите текст вопроса' });
      return;
    }
    try {
      await authorizedFetch('/admin/questions', {
        method: 'POST',
        body: JSON.stringify({
          category_id: Number(questionForm.categoryId),
          text: questionForm.text.trim(),
          order: Number(questionForm.order) || 0,
          is_active: true,
        }),
      });
      setQuestionForm((prev) => ({ ...prev, text: '' }));
      await loadAllData();
      setPanelMessage({ type: 'success', message: 'Вопрос добавлен' });
    } catch (error) {
      setPanelMessage({ type: 'error', message: error.message });
    }
  };

  const handleToggleQuestion = async (questionId, newStatus) => {
    try {
      await authorizedFetch(`/admin/questions/${questionId}`, {
        method: 'PUT',
        body: JSON.stringify({ is_active: newStatus }),
      });
      await loadAllData();
      setPanelMessage({ type: 'success', message: 'Статус вопроса обновлён' });
    } catch (error) {
      setPanelMessage({ type: 'error', message: error.message });
    }
  };

  const handleDeleteQuestion = async (questionId) => {
    if (!window.confirm('Удалить вопрос?')) return;
    try {
      await authorizedFetch(`/admin/questions/${questionId}`, { method: 'DELETE' });
      await loadAllData();
      setPanelMessage({ type: 'success', message: 'Вопрос удалён' });
    } catch (error) {
      setPanelMessage({ type: 'error', message: error.message });
    }
  };

  const handleAddWord = async (type) => {
    const text = wordForms[type].trim();
    if (!text) {
      setPanelMessage({ type: 'error', message: 'Введите текст' });
      return;
    }
    try {
      await authorizedFetch(`/admin/random-names/${type === 'adjective' ? 'adjectives' : 'nouns'}`, {
        method: 'POST',
        body: JSON.stringify({ text }),
      });
      setWordForms((prev) => ({ ...prev, [type]: '' }));
      await loadWords();
      setPanelMessage({ type: 'success', message: 'Слово добавлено' });
    } catch (error) {
      setPanelMessage({ type: 'error', message: error.message });
    }
  };

  const handleToggleWord = async (type, word) => {
    try {
      await authorizedFetch(`/admin/random-names/${type}/${word.id}`, {
        method: 'PUT',
        body: JSON.stringify({ is_active: !word.is_active }),
      });
      await loadWords();
    } catch (error) {
      setPanelMessage({ type: 'error', message: error.message });
    }
  };

  const handleDeleteWord = async (type, wordId) => {
    if (!window.confirm('Удалить слово?')) return;
    try {
      await authorizedFetch(`/admin/random-names/${type}/${wordId}`, { method: 'DELETE' });
      await loadWords();
    } catch (error) {
      setPanelMessage({ type: 'error', message: error.message });
    }
  };

  if (!token) {
    return (
      <div className="admin-layout">
        <div className="admin-login-container">
        <form className="admin-card admin-login" onSubmit={handleLogin}>
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
              onChange={(e) => setLoginForm((prev) => ({ ...prev, username: e.target.value }))}
            />
          </label>
          <label>
            Пароль
            <input
              type="password"
              value={loginForm.password}
              onChange={(e) => setLoginForm((prev) => ({ ...prev, password: e.target.value }))}
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

  return (
    <div className="admin-layout">
      <nav className="admin-navigation">
          <h1>Админ-панель SoftSpeak</h1>
        <div className="admin-navigation-actions">
          <button className="admin-btn ghost" onClick={loadAllData} disabled={loading}>
            ⟳ Обновить
          </button>
          <button className="admin-btn danger" onClick={handleLogout}>
            Выйти
          </button>
        </div>
      </nav>

      <div className="admin-content">
      {panelMessage.message && (
        <div className={`admin-alert ${panelMessage.type}`}>{panelMessage.message}</div>
      )}

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

      <section className="admin-section">
        <h2>Добавить вопрос</h2>
        <form className="question-form" onSubmit={handleAddQuestion}>
          <label>
            Категория
            <select
              value={questionForm.categoryId}
              onChange={(e) => setQuestionForm((prev) => ({ ...prev, categoryId: e.target.value }))}
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
              onChange={(e) => setQuestionForm((prev) => ({ ...prev, text: e.target.value }))}
            />
          </label>
          <label>
            Порядок
            <input
              type="number"
              value={questionForm.order}
              onChange={(e) => setQuestionForm((prev) => ({ ...prev, order: e.target.value }))}
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
                        onClick={() => handleToggleQuestion(q.id, !q.is_active)}
                      >
                        {q.is_active ? 'Скрыть' : 'Показать'}
                      </button>
                      <button
                        className="admin-btn danger"
                        type="button"
                        onClick={() => handleDeleteQuestion(q.id)}
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
                      setWordForms((prev) => ({ ...prev, [type]: e.target.value }))
                    }
                  />
                  <button
                    className="admin-btn primary"
                    type="button"
                    onClick={() => handleAddWord(type)}
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
                            handleToggleWord(
                              type === 'adjective' ? 'adjectives' : 'nouns',
                              word,
                            )
                          }
                        >
                          {word.is_active ? 'Выключить' : 'Включить'}
                        </button>
                        <button
                          className="admin-btn danger"
                          type="button"
                          onClick={() =>
                            handleDeleteWord(type === 'adjective' ? 'adjectives' : 'nouns', word.id)
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

      <section className="admin-section">
        <div className="section-header">
          <h2>Жалобы пользователей</h2>
        </div>
        <div className="reports-container">
          <div className="reports-filter">
            <button
              className={`admin-btn ${reportStatusFilter === 'pending' ? 'primary' : 'ghost'}`}
              onClick={() => {
                setReportStatusFilter('pending');
                setShowBannedUsers(false);
              }}
            >
              Ожидают ({reports.filter(r => r.status === 'pending').length})
            </button>
            <button
              className={`admin-btn ${reportStatusFilter === '' ? 'primary' : 'ghost'}`}
              onClick={() => {
                setReportStatusFilter('');
                setShowBannedUsers(false);
              }}
            >
              Все ({reports.length})
            </button>
            <button
              className={`admin-btn ${showBannedUsers ? 'primary' : 'ghost'}`}
              onClick={() => {
                setShowBannedUsers(true);
                setReportStatusFilter('');
                setSelectedReport(null);
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
                        onClick={() => handleUnbanUser(user.id)}
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
                  onClick={() => handleViewReport(report)}
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
                setSelectedReport(null);
                setReportMessages([]);
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
                onClick={() => handleBanUser(selectedReport.id)}
              >
                Забанить пользователя
              </button>
              <button
                className="admin-btn primary"
                onClick={() => handleRejectReport(selectedReport.id)}
              >
                Отклонить жалобу
              </button>
            </div>
          )}
        </section>
      )}
      </div>
    </div>
  );
}

export default Admin;

