import { useState, useCallback, useEffect } from 'react';
import { useWindowManager } from './hooks/useWindowManager';
import Window from './components/Window';
import Taskbar from './components/Taskbar';
import FileManager from './components/FileManager';
import ChatAssistant from './components/ChatAssistant';
import { uploadFile, checkHealth } from './services/api';
import './styles/theme.css';
import './styles/desktop.css';

export default function App() {
  const { windows, focusedId, openWindow, closeWindow, minimizeWindow, maximizeWindow, focusWindow, moveWindow, resizeWindow } = useWindowManager();
  const [dragging, setDragging] = useState(false);
  const [ollamaStatus, setOllamaStatus] = useState<'connected' | 'connecting' | 'error'>('connecting');

  useEffect(() => {
    const check = async () => {
      const ok = await checkHealth();
      setOllamaStatus(ok ? 'connected' : 'error');
    };
    check();
    const iv = setInterval(check, 10000);
    return () => clearInterval(iv);
  }, []);

  useEffect(() => {
    openWindow('files', 'File Manager — ~/Documents', '📁', 'files', 750, 450);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleOpenApp = useCallback((id: string) => {
    switch (id) {
      case 'files':
        openWindow('files', 'File Manager — ~/Documents', '📁', 'files', 750, 450);
        break;
      case 'chat':
        openWindow('chat', 'TeardownOS Assistant', '🔬', 'chat', 900, 600);
        break;
    }
  }, [openWindow]);

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.dataTransfer.types.includes('Files')) {
      setDragging(true);
    }
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.currentTarget === e.target || !e.currentTarget.contains(e.relatedTarget as Node)) {
      setDragging(false);
    }
  }, []);

  const handleDrop = useCallback(async (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragging(false);

    const files = Array.from(e.dataTransfer.files);
    if (files.length === 0) return;

    openWindow('files', 'File Manager — ~/Documents', '📁', 'files', 750, 450);

    for (const file of files) {
      try {
        await uploadFile(file);
      } catch (err) {
        console.error(`Failed to upload ${file.name}:`, err);
      }
    }
  }, [openWindow]);

  const renderWindowContent = (component: string) => {
    switch (component) {
      case 'files': return <FileManager />;
      case 'chat': return <ChatAssistant />;
      default: return <div style={{ padding: 16 }}>Unknown component</div>;
    }
  };

  return (
    <div
      className="desktop"
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
    >
      {/* Desktop Icons */}
      <div className="desktop__icons">
        <div className="desktop-icon" onDoubleClick={() => handleOpenApp('files')}>
          <span className="desktop-icon__icon">📁</span>
          <span className="desktop-icon__label">Documents</span>
        </div>
        <div className="desktop-icon" onDoubleClick={() => handleOpenApp('chat')}>
          <span className="desktop-icon__icon">🔬</span>
          <span className="desktop-icon__label">Assistant</span>
        </div>
      </div>

      {/* Windows */}
      {windows.map(win => (
        <Window
          key={win.id}
          win={win}
          focused={focusedId === win.id}
          onClose={() => closeWindow(win.id)}
          onMinimize={() => minimizeWindow(win.id)}
          onMaximize={() => maximizeWindow(win.id)}
          onFocus={() => focusWindow(win.id)}
          onMove={(x, y) => moveWindow(win.id, x, y)}
          onResize={(w, h) => resizeWindow(win.id, w, h)}
        >
          {renderWindowContent(win.component)}
        </Window>
      ))}

      {/* Drag overlay */}
      {dragging && (
        <div className="desktop__drop-overlay">
          <div className="desktop__drop-overlay-inner">
            <div className="icon">📥</div>
            <div className="title">Drop files to upload</div>
            <div className="subtitle">Files will appear in ~/Documents and be automatically indexed</div>
          </div>
        </div>
      )}

      {/* Taskbar */}
      <Taskbar
        windows={windows}
        focusedId={focusedId}
        onFocusWindow={focusWindow}
        onOpenApp={handleOpenApp}
        ollamaStatus={ollamaStatus}
      />
    </div>
  );
}
