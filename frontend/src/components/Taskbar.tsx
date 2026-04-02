import { useState, useEffect } from 'react';
import type { WindowState } from '../hooks/useWindowManager';
import '../styles/taskbar.css';

interface TaskbarProps {
  windows: WindowState[];
  focusedId: string | null;
  onFocusWindow: (id: string) => void;
  onOpenApp: (id: string) => void;
  ollamaStatus: 'connected' | 'connecting' | 'error';
}

export default function Taskbar({ windows, focusedId, onFocusWindow, onOpenApp, ollamaStatus }: TaskbarProps) {
  const [time, setTime] = useState('');

  useEffect(() => {
    const update = () => {
      const now = new Date();
      setTime(now.toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit' }));
    };
    update();
    const iv = setInterval(update, 1000);
    return () => clearInterval(iv);
  }, []);

  const statusClass = ollamaStatus === 'connected' ? '' : ollamaStatus === 'connecting' ? 'status-dot--warning' : 'status-dot--error';

  return (
    <div className="taskbar">
      <div className="taskbar__start" onClick={() => onOpenApp('files')}>
        <span className="logo">🔬</span>
        <span>TeardownOS</span>
      </div>

      <div className="taskbar__items">
        {windows.map(w => (
          <div
            key={w.id}
            className={`taskbar__item ${focusedId === w.id ? 'taskbar__item--active' : ''}`}
            onClick={() => onFocusWindow(w.id)}
          >
            <span className="icon">{w.icon}</span>
            <span>{w.title}</span>
          </div>
        ))}
      </div>

      <div className="taskbar__tray">
        <div className={`status-dot ${statusClass}`} title={`Ollama: ${ollamaStatus}`} />
        <span>{time}</span>
      </div>
    </div>
  );
}
