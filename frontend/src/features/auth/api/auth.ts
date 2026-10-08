import { useMutation } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { queryClient } from "@/lib/queryClient";

interface LoginRequest {
  email: string;
  password: string;
}

interface RegisterRequest {
  email: string;
  password: string;
}

interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

function storeTokens(data: TokenResponse) {
  localStorage.setItem("access_token", data.access_token);
  localStorage.setItem("refresh_token", data.refresh_token);
}

export function useLogin() {
  return useMutation({
    mutationFn: async (data: LoginRequest): Promise<TokenResponse> => {
      const response = await api.post("/auth/login", data, {
        skipAuthRefresh: true,
      });
      return response.data;
    },
    onSuccess: storeTokens,
  });
}

export function useRegister() {
  return useMutation({
    mutationFn: async (data: RegisterRequest): Promise<TokenResponse> => {
      const response = await api.post("/auth/register", data, {
        skipAuthRefresh: true,
      });
      return response.data;
    },
    onSuccess: storeTokens,
  });
}

export function useLogout() {
  return useMutation({
    mutationFn: async () => {
      const refreshToken = localStorage.getItem("refresh_token");
      await api.post(
        "/auth/logout",
        refreshToken ? { refresh_token: refreshToken } : undefined,
      );
    },
    onSuccess: () => {
      localStorage.removeItem("access_token");
      localStorage.removeItem("refresh_token");
      queryClient.clear();
    },
    onError: () => {
      localStorage.removeItem("access_token");
      localStorage.removeItem("refresh_token");
      queryClient.clear();
    },
  });
}

interface UserResponse {
  id: string;
  email: string;
  created_at: string;
}

export async function fetchCurrentUser(): Promise<UserResponse> {
  const response = await api.get("/auth/me");
  return response.data;
}
