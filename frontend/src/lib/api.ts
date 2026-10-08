import axios, {
  type AxiosError,
  type AxiosRequestConfig,
  type InternalAxiosRequestConfig,
} from "axios";
import { queryClient } from "./queryClient";

declare module "axios" {
  interface AxiosRequestConfig {
    _retry?: boolean;
    skipAuthRefresh?: boolean;
  }
}

const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

export const api = axios.create({
  baseURL: `${API_URL}/api/v1`,
  headers: {
    "Content-Type": "application/json",
  },
});

interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

let refreshPromise: Promise<string> | null = null;

function clearSession() {
  localStorage.removeItem("access_token");
  localStorage.removeItem("refresh_token");
  queryClient.clear();
}

function redirectToLogin() {
  if (window.location.pathname !== "/login") {
    window.location.href = "/login";
  }
}

async function refreshAccessToken(): Promise<string> {
  const refreshToken = localStorage.getItem("refresh_token");
  if (!refreshToken) {
    throw new Error("No refresh token available");
  }

  // Use the base Axios client to keep a failed refresh from recursively
  // entering the response interceptor.
  const response = await axios.post<TokenResponse>(
    `${API_URL}/api/v1/auth/refresh`,
    { refresh_token: refreshToken },
    { headers: { "Content-Type": "application/json" } },
  );
  localStorage.setItem("access_token", response.data.access_token);
  localStorage.setItem("refresh_token", response.data.refresh_token);
  return response.data.access_token;
}

// Request interceptor: attach Bearer token
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem("access_token");
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor: handle 401
api.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const config = error.config as
      | (InternalAxiosRequestConfig & AxiosRequestConfig)
      | undefined;
    const shouldRefresh =
      error.response?.status === 401 &&
      config !== undefined &&
      Boolean(localStorage.getItem("refresh_token")) &&
      !config._retry &&
      !config.skipAuthRefresh;

    if (!shouldRefresh) {
      if (error.response?.status === 401 && !config?.skipAuthRefresh) {
        clearSession();
        redirectToLogin();
      }
      return Promise.reject(error);
    }

    config._retry = true;
    try {
      refreshPromise ??= refreshAccessToken().finally(() => {
        refreshPromise = null;
      });
      const accessToken = await refreshPromise;
      config.headers.Authorization = `Bearer ${accessToken}`;
      return api(config);
    } catch (refreshError) {
      clearSession();
      redirectToLogin();
      return Promise.reject(refreshError);
    }
  },
);
