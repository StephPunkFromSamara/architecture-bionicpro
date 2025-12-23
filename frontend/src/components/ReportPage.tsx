import React, { useEffect, useState } from 'react';
import keycloak from '../keycloak';

interface ReportData {
  user_id: number;
  name: string;
  age: number;
  prosthesis_id: string;
  usage_hours: number;
  temperature: number;
}

const ReportPage: React.FC = () => {
  const [initialized, setInitialized] = useState(false);
  const [token, setToken] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [reportData, setReportData] = useState<ReportData | null>(null);

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

  const fetchReport = async () => {
    if (!token) {
      setError('Not authenticated');
      return;
    }

    try {
      setLoading(true);
      setError(null);
      setReportData(null);

      // @ts-ignore
      const apiUrl = (typeof window !== 'undefined' && (window as any)._env_ && (window as any)._env_.REACT_APP_API_URL) 
        ? (window as any)._env_.REACT_APP_API_URL 
        : process.env.REACT_APP_API_URL || 'http://localhost:8000';
      const response = await fetch(`${apiUrl}/reports`, {
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ detail: 'Failed to fetch report' }));
        throw new Error(errorData.detail || `HTTP error! status: ${response.status}`);
      }

      const data: ReportData = await response.json();
      setReportData(data);
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
        <div className="p-8 bg-white rounded-lg shadow-md w-full max-w-2xl">
          <h1 className="text-2xl font-bold mb-6">Usage Reports</h1>

          <button
              onClick={fetchReport}
              disabled={loading}
              className={`px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600 ${
                  loading ? 'opacity-50 cursor-not-allowed' : ''
              }`}
          >
            {loading ? 'Loading Report...' : 'Get My Report'}
          </button>

          {error && (
              <div className="mt-4 p-4 bg-red-100 text-red-700 rounded">
                {error}
              </div>
          )}

          {reportData && (
              <div className="mt-6 p-6 bg-gray-50 rounded-lg">
                <h2 className="text-xl font-semibold mb-4">Your Report</h2>
                <div className="space-y-3">
                  <div className="flex justify-between">
                    <span className="font-medium">User ID:</span>
                    <span>{reportData.user_id}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="font-medium">Name:</span>
                    <span>{reportData.name}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="font-medium">Age:</span>
                    <span>{reportData.age}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="font-medium">Prosthesis ID:</span>
                    <span>{reportData.prosthesis_id}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="font-medium">Usage Hours:</span>
                    <span>{reportData.usage_hours.toFixed(2)} hours</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="font-medium">Temperature:</span>
                    <span>{reportData.temperature.toFixed(1)}°C</span>
                  </div>
                </div>
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