import { create } from "zustand";

type UiState = {
  apiBaseUrl: string;
  sidebarCollapsed: boolean;
  setSidebarCollapsed: (value: boolean) => void;
  hydrateFromEnv: () => void;
};

const DEFAULT_API = "http://127.0.0.1:8000/api/v1";

export const useUiStore = create<UiState>((set) => ({
  apiBaseUrl: DEFAULT_API,
  sidebarCollapsed: false,
  setSidebarCollapsed: (value) => set({ sidebarCollapsed: value }),
  hydrateFromEnv: () => {
    const fromEnv = process.env.NEXT_PUBLIC_API_BASE_URL;
    if (fromEnv) {
      set({ apiBaseUrl: fromEnv });
    }
  },
}));
