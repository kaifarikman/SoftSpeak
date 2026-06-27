import { useEffect, useMemo, useState } from 'react';
import '../css/Admin.css';
import { API_URL } from '../config';
import {
  AdminLoginPanel,
  NamesPanel,
  QuestionsPanel,
  ReportsPanel,
  StatsPanel,
} from '../components/admin/AdminPanels';

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
      <AdminLoginPanel
        loginForm={loginForm}
        loginStatus={loginStatus}
        loading={loading}
        onLogin={handleLogin}
        onLoginFormChange={setLoginForm}
      />
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

      <StatsPanel stats={stats} />

      <QuestionsPanel
        categories={categories}
        questionsByCategory={questionsByCategory}
        questionForm={questionForm}
        loading={loading}
        onQuestionFormChange={setQuestionForm}
        onAddQuestion={handleAddQuestion}
        onToggleQuestion={handleToggleQuestion}
        onDeleteQuestion={handleDeleteQuestion}
      />

      <NamesPanel
        words={words}
        wordForms={wordForms}
        onWordFormsChange={setWordForms}
        onAddWord={handleAddWord}
        onToggleWord={handleToggleWord}
        onDeleteWord={handleDeleteWord}
      />

      <ReportsPanel
        reports={reports}
        selectedReport={selectedReport}
        reportMessages={reportMessages}
        reportStatusFilter={reportStatusFilter}
        bannedUsers={bannedUsers}
        showBannedUsers={showBannedUsers}
        onStatusFilterChange={setReportStatusFilter}
        onShowBannedUsersChange={setShowBannedUsers}
        onSelectedReportChange={setSelectedReport}
        onReportMessagesChange={setReportMessages}
        onViewReport={handleViewReport}
        onBanUser={handleBanUser}
        onRejectReport={handleRejectReport}
        onUnbanUser={handleUnbanUser}
      />
      </div>
    </div>
  );
}

export default Admin;
