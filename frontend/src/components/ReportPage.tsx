import React, { useEffect, useState } from 'react';
import keycloak from '../keycloak';

const ReportPage: React.FC = () => {
  const [initialized, setInitialized] = useState(false);
  const [token, setToken] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    // ✅ Инициализация Keycloak с PKCE
    keycloak
        .init({
          pkceMethod: 'S256', // включает PKCE flow
          checkLoginIframe: false,
          onLoad: 'login-required', // требует авторизацию сразу
        })
        .then((authenticated) => {
          if (authenticated) {
            setToken(keycloak.token!);
          } else {
            keycloak.login();
          }
          setInitialized(true);

          // ⏱ Автоматическое обновление токена
          const refreshInterval = setInterval(() => {
            keycloak
                .updateToken(60)
                .then((refreshed) => {
                  if (refreshed) {
                    setToken(keycloak.token!);
                  }
                })
                .catch(() => keycloak.login());
          }, 60000);

          return () => clearInterval(refreshInterval);
        })
        .catch((err) => {
          console.error('Keycloak init failed:', err);
          setError('Failed to initialize authentication');
        });
  }, []);

  const downloadReport = async () => {
    if (!token) {
      setError('Not authenticated');
      return;
    }

    try {
      setLoading(true);
      setError(null);

      const response = await fetch(`${process.env.REACT_APP_API_URL}/reports`, {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });

      if (!response.ok) throw new Error('Failed to download report');

      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = 'report.pdf';
      link.click();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred');
    } finally {
      setLoading(false);
    }
  };

  if (!initialized) {
    return <div>Loading authentication...</div>;
  }

  return (
      <div className="flex flex-col items-center justify-center min-h-screen bg-gray-100">
        <div className="p-8 bg-white rounded-lg shadow-md">
          <h1 className="text-2xl font-bold mb-6">Usage Reports</h1>

          <button
              onClick={downloadReport}
              disabled={loading}
              className={`px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600 ${
                  loading ? 'opacity-50 cursor-not-allowed' : ''
              }`}
          >
            {loading ? 'Generating Report...' : 'Download Report'}
          </button>

          {error && (
              <div className="mt-4 p-4 bg-red-100 text-red-700 rounded">
                {error}
              </div>
          )}

          <button
              onClick={() => keycloak.logout({ redirectUri: window.location.origin })}
              className="mt-6 text-sm text-gray-600 hover:text-gray-800"
          >
            Logout
          </button>
        </div>
      </div>
  );
};

export default ReportPage;