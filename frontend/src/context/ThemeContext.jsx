// frontend/src/context/ThemeContext.jsx
import React, { createContext, useContext, useEffect, useState } from 'react';

/*****
 * Theme Context for SuperBrowser
 * Manages dark mode / light mode switching globally
 * Persists user preference in localStorage
 ******/
const ThemeContext = createContext();

export function ThemeProvider({ children }) {
  const [theme, setTheme] = useState(() => {
    // Load theme from localStorage, or default to 'light'
    const savedTheme = localStorage.getItem('superbrowser-theme');
    
    if (savedTheme) {
      return savedTheme;
    }

    // Check system preference for dark mode
    if (
      window.matchMedia &&
      window.matchMedia('(prefers-color-scheme: dark)').matches
    ) {
      return 'dark';
    }

    return 'light';
  });

  // Update document attribute and localStorage when theme changes
  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem('superbrowser-theme', theme);
  }, [theme]);

  // Listen for system theme changes
  useEffect(() => {
    const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
    const handleChange = (e) => {
      // Only auto-change if user hasn't manually set a preference
      if (!localStorage.getItem('superbrowser-theme')) {
        setTheme(e.matches ? 'dark' : 'light');
      }
    };

    // Modern browsers
    if (mediaQuery.addEventListener) {
      mediaQuery.addEventListener('change', handleChange);
      return () => mediaQuery.removeEventListener('change', handleChange);
    }
    // Older browsers
    else if (mediaQuery.addListener) {
      mediaQuery.addListener(handleChange);
      return () => mediaQuery.removeListener(handleChange);
    }
  }, []);

  // Toggle between light and dark
  const toggleTheme = () => {
    setTheme((prevTheme) => (prevTheme === 'light' ? 'dark' : 'light'));
  };

  const value = {
    theme,
    toggleTheme,
    isDark: theme === 'dark',
    isLight: theme === 'light',
  };

  return (
    <ThemeContext.Provider value={value}>
      {children}
    </ThemeContext.Provider>
  );
}

/**
 * Custom hook to use theme context
 * @throws {Error} If used outside ThemeProvider
 * @returns {Object} Theme context with theme, toggleTheme, isDark, isLight
 */
export function useTheme() {
  const context = useContext(ThemeContext);
  if (!context) {
    throw new Error('useTheme must be used within ThemeProvider');
  }
  return context;
}