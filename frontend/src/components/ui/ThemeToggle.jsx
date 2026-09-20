import React, { useEffect, useState } from 'react';
import { Sun, Moon } from 'lucide-react';
import './ThemeToggle.css';

export const ThemeToggle = () => {
  const [theme, setTheme] = useState(() => {
    return localStorage.getItem('modelpulse-theme') || 'light';
  });

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem('modelpulse-theme', theme);
  }, [theme]);

  const toggleTheme = () => {
    setTheme(prev => prev === 'light' ? 'dark' : 'light');
  };

  return (
    <button 
      className="theme-toggle" 
      onClick={toggleTheme}
      aria-label={`Switch to ${theme === 'light' ? 'dark' : 'light'} mode`}
    >
      <div className={`theme-toggle-icon ${theme === 'dark' ? 'rotate' : ''}`}>
        {theme === 'light' ? <Moon size={20} /> : <Sun size={20} />}
      </div>
    </button>
  );
};

export default ThemeToggle;
