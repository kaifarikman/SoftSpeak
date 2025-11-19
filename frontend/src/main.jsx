import React from 'react';
import ReactDOM from 'react-dom/client';
import { BrowserRouter } from 'react-router-dom';
import App from './App';
import { ChatDataProvider } from './context/ChatDataContext';
import ErrorBoundary from './components/ErrorBoundary';
import './css/App.css';

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <ErrorBoundary>
      <BrowserRouter>
        <ChatDataProvider>
          <App />
        </ChatDataProvider>
      </BrowserRouter>
    </ErrorBoundary>
  </React.StrictMode>
);
