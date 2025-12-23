import Keycloak from 'keycloak-js';

// Используем runtime конфигурацию из window._env_ или fallback на process.env
const getEnvVar = (key: string, defaultValue?: string): string => {
  // @ts-ignore
  if (typeof window !== 'undefined' && window._env_ && window._env_[key]) {
    // @ts-ignore
    return window._env_[key];
  }
  return process.env[key] || defaultValue || '';
};

const url = getEnvVar('REACT_APP_KEYCLOAK_URL');
const realm = getEnvVar('REACT_APP_KEYCLOAK_REALM');
const clientId = getEnvVar('REACT_APP_KEYCLOAK_CLIENT_ID');

if (!url || !realm || !clientId) {
  throw new Error(`Keycloak env variables are not defined. url=${url}, realm=${realm}, clientId=${clientId}`);
}

const keycloak = new Keycloak({
  url,
  realm,
  clientId,
});

export default keycloak;