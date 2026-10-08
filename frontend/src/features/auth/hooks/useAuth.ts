import { useQuery } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import { useLogout, fetchCurrentUser } from "../api/auth";
import { queryClient } from "@/lib/queryClient";

export function useAuth() {
  const navigate = useNavigate();
  const logoutMutation = useLogout();

  const token = localStorage.getItem("access_token");
  const isAuthenticated = !!token;

  const {
    data: user,
    isLoading,
    error,
  } = useQuery({
    queryKey: ["currentUser"],
    queryFn: fetchCurrentUser,
    enabled: isAuthenticated,
    retry: false,
  });

  const logout = () => {
    queryClient.clear();
    logoutMutation.mutate(undefined, {
      onSuccess: () => {
        navigate("/login");
      },
      onError: () => {
        navigate("/login");
      },
    });
  };

  return {
    user,
    isAuthenticated,
    isLoading,
    error,
    logout,
  };
}
