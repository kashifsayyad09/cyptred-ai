import React from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import LandingPage from './pages/LandingPage';
import ExamPage from './pages/ExamPage';
import DashboardPage from './pages/DashboardPage';
import SessionDetailPage from './pages/SessionDetailPage';
import NotFoundPage from './pages/NotFoundPage';

const App: React.FC = () => {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/"                              element={<LandingPage />} />
        <Route path="/exam/:examId"                  element={<ExamPage />} />
        <Route path="/dashboard"                     element={<DashboardPage />} />
        <Route path="/dashboard/session/:sessionId"  element={<SessionDetailPage />} />
        <Route path="*"                              element={<NotFoundPage />} />
      </Routes>
    </BrowserRouter>
  );
};

export default App;
