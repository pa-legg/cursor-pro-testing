import { useRef, useCallback, type ReactNode } from 'react';
import type { WindowState } from '../hooks/useWindowManager';
import '../styles/window.css';

interface WindowProps {
  win: WindowState;
  focused: boolean;
  onClose: () => void;
  onMinimize: () => void;
  onMaximize: () => void;
  onFocus: () => void;
  onMove: (x: number, y: number) => void;
  onResize: (w: number, h: number) => void;
  children: ReactNode;
}

export default function Window({ win, focused, onClose, onMinimize, onMaximize, onFocus, onMove, onResize, children }: WindowProps) {
  const dragRef = useRef<{ startX: number; startY: number; winX: number; winY: number } | null>(null);
  const resizeRef = useRef<{ startX: number; startY: number; winW: number; winH: number } | null>(null);

  const handleDragStart = useCallback((e: React.MouseEvent) => {
    if (win.maximized) return;
    onFocus();
    dragRef.current = { startX: e.clientX, startY: e.clientY, winX: win.x, winY: win.y };

    const handleMove = (ev: MouseEvent) => {
      if (!dragRef.current) return;
      const dx = ev.clientX - dragRef.current.startX;
      const dy = ev.clientY - dragRef.current.startY;
      onMove(dragRef.current.winX + dx, dragRef.current.winY + dy);
    };

    const handleUp = () => {
      dragRef.current = null;
      document.removeEventListener('mousemove', handleMove);
      document.removeEventListener('mouseup', handleUp);
    };

    document.addEventListener('mousemove', handleMove);
    document.addEventListener('mouseup', handleUp);
  }, [win.x, win.y, win.maximized, onFocus, onMove]);

  const handleResizeStart = useCallback((e: React.MouseEvent) => {
    if (win.maximized) return;
    e.stopPropagation();
    resizeRef.current = { startX: e.clientX, startY: e.clientY, winW: win.width, winH: win.height };

    const handleMove = (ev: MouseEvent) => {
      if (!resizeRef.current) return;
      const dw = ev.clientX - resizeRef.current.startX;
      const dh = ev.clientY - resizeRef.current.startY;
      onResize(resizeRef.current.winW + dw, resizeRef.current.winH + dh);
    };

    const handleUp = () => {
      resizeRef.current = null;
      document.removeEventListener('mousemove', handleMove);
      document.removeEventListener('mouseup', handleUp);
    };

    document.addEventListener('mousemove', handleMove);
    document.addEventListener('mouseup', handleUp);
  }, [win.width, win.height, win.maximized, onResize]);

  if (win.minimized) return null;

  const style: React.CSSProperties = win.maximized
    ? { zIndex: win.zIndex }
    : { left: win.x, top: win.y, width: win.width, height: win.height, zIndex: win.zIndex };

  return (
    <div
      className={`window ${focused ? 'window--focused' : ''} ${win.maximized ? 'window--maximized' : ''}`}
      style={style}
      onMouseDown={onFocus}
    >
      <div className="window__titlebar" onMouseDown={handleDragStart} onDoubleClick={onMaximize}>
        <span className="window__titlebar-icon">{win.icon}</span>
        <span className="window__titlebar-text">{win.title}</span>
        <div className="window__controls">
          <button className="window__control window__control--minimize" onClick={onMinimize} title="Minimize" />
          <button className="window__control window__control--maximize" onClick={onMaximize} title="Maximize" />
          <button className="window__control window__control--close" onClick={onClose} title="Close" />
        </div>
      </div>
      <div className="window__content">
        {children}
      </div>
      {!win.maximized && (
        <div className="window__resize-handle" onMouseDown={handleResizeStart} />
      )}
    </div>
  );
}
