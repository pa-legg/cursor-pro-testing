import { useState, useCallback } from 'react';

export interface WindowState {
  id: string;
  title: string;
  icon: string;
  x: number;
  y: number;
  width: number;
  height: number;
  minimized: boolean;
  maximized: boolean;
  zIndex: number;
  component: string;
}

let nextZ = 100;

export function useWindowManager() {
  const [windows, setWindows] = useState<WindowState[]>([]);
  const [focusedId, setFocusedId] = useState<string | null>(null);

  const openWindow = useCallback((id: string, title: string, icon: string, component: string, width = 800, height = 500) => {
    setWindows(prev => {
      const existing = prev.find(w => w.id === id);
      if (existing) {
        nextZ++;
        return prev.map(w =>
          w.id === id ? { ...w, minimized: false, zIndex: nextZ } : w
        );
      }
      nextZ++;
      const x = 80 + (prev.length % 5) * 30;
      const y = 40 + (prev.length % 5) * 30;
      return [...prev, { id, title, icon, x, y, width, height, minimized: false, maximized: false, zIndex: nextZ, component }];
    });
    setFocusedId(id);
  }, []);

  const closeWindow = useCallback((id: string) => {
    setWindows(prev => prev.filter(w => w.id !== id));
    setFocusedId(null);
  }, []);

  const minimizeWindow = useCallback((id: string) => {
    setWindows(prev => prev.map(w =>
      w.id === id ? { ...w, minimized: true } : w
    ));
    setFocusedId(null);
  }, []);

  const maximizeWindow = useCallback((id: string) => {
    setWindows(prev => prev.map(w =>
      w.id === id ? { ...w, maximized: !w.maximized } : w
    ));
  }, []);

  const focusWindow = useCallback((id: string) => {
    nextZ++;
    setWindows(prev => prev.map(w =>
      w.id === id ? { ...w, zIndex: nextZ, minimized: false } : w
    ));
    setFocusedId(id);
  }, []);

  const moveWindow = useCallback((id: string, x: number, y: number) => {
    setWindows(prev => prev.map(w =>
      w.id === id ? { ...w, x, y } : w
    ));
  }, []);

  const resizeWindow = useCallback((id: string, width: number, height: number) => {
    setWindows(prev => prev.map(w =>
      w.id === id ? { ...w, width: Math.max(400, width), height: Math.max(300, height) } : w
    ));
  }, []);

  return {
    windows,
    focusedId,
    openWindow,
    closeWindow,
    minimizeWindow,
    maximizeWindow,
    focusWindow,
    moveWindow,
    resizeWindow,
  };
}
