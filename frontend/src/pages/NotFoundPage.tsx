import React from 'react';
import { useNavigate } from 'react-router-dom';

const NotFoundPage: React.FC = () => {
  const navigate = useNavigate();
  return (
    <div style={{ padding: '4rem 2rem', textAlign: 'center' }}>
      <h1 style={{ fontSize: '4rem', color: '#374151' }}>404</h1>
      <p style={{ color: '#9ca3af', marginBottom: '2rem' }}>Page not found.</p>
      <button
        onClick={() => navigate('/')}
        style={{ background: '#3b82f6', color: '#fff', border: 'none', padding: '0.6rem 1.5rem', borderRadius: '6px' }}
      >
        Go Home
      </button>
    </div>
  );
};

export default NotFoundPage;
