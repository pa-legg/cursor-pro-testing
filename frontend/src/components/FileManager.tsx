import { useState, useEffect, useCallback } from 'react';
import { getDocuments, deleteDocument, type Document } from '../services/api';
import '../styles/filemanager.css';

function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function formatTime(iso: string): string {
  const d = new Date(iso);
  return d.toLocaleString('en-GB', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
}

function getFileIcon(fileType: string): string {
  const icons: Record<string, string> = {
    pdf: '📄', png: '🖼️', jpg: '🖼️', jpeg: '🖼️', gif: '🖼️', bmp: '🖼️', tiff: '🖼️', svg: '🖼️',
    py: '🐍', js: '📜', ts: '📜', java: '☕', c: '⚙️', cpp: '⚙️', rs: '🦀', go: '🔷',
    txt: '📝', md: '📝', csv: '📊', json: '📋', xml: '📋', html: '🌐', htm: '🌐',
    sh: '💻', yaml: '⚙️', yml: '⚙️', toml: '⚙️',
  };
  return icons[fileType] || '📁';
}

function getStatusLabel(status: string): { label: string; icon: string } {
  switch (status) {
    case 'queued': return { label: 'Queued', icon: '⏳' };
    case 'processing': return { label: 'Processing', icon: '' };
    case 'indexed': return { label: 'Indexed', icon: '✓' };
    case 'error': return { label: 'Error', icon: '✗' };
    default: return { label: status, icon: '' };
  }
}

export default function FileManager() {
  const [documents, setDocuments] = useState<Document[]>([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [filterType, setFilterType] = useState<string>('all');

  useEffect(() => {
    let cancelled = false;
    const doRefresh = async () => {
      try {
        const docs = await getDocuments();
        if (!cancelled) setDocuments(docs);
      } catch { /* offline */ }
    };
    doRefresh();
    const iv = setInterval(doRefresh, 3000);
    return () => { cancelled = true; clearInterval(iv); };
  }, []);

  const handleDelete = useCallback(async (docId: string, filename: string) => {
    if (!confirm(`Delete "${filename}" and remove from index?`)) return;
    try {
      await deleteDocument(docId);
      setDocuments(prev => prev.filter(d => d.id !== docId));
    } catch { /* ignore */ }
  }, []);

  const filteredDocs = documents.filter(doc => {
    const matchesSearch = !searchQuery ||
      doc.filename.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesType = filterType === 'all' || doc.file_type === filterType;
    return matchesSearch && matchesType;
  });

  const fileTypes = [...new Set(documents.map(d => d.file_type))].sort();
  const totalSize = documents.reduce((s, d) => s + d.file_size, 0);
  const indexedCount = documents.filter(d => d.status === 'indexed').length;

  return (
    <div className="file-manager">
      <div className="file-manager__toolbar">
        <span>📁</span>
        <div className="file-manager__path">~/Documents</div>
      </div>

      <div className="file-manager__search-bar">
        <input
          type="text"
          className="file-manager__search-input"
          placeholder="Search files..."
          value={searchQuery}
          onChange={e => setSearchQuery(e.target.value)}
        />
        <select
          className="file-manager__filter-select"
          value={filterType}
          onChange={e => setFilterType(e.target.value)}
        >
          <option value="all">All types</option>
          {fileTypes.map(t => (
            <option key={t} value={t}>.{t}</option>
          ))}
        </select>
      </div>

      <div className="file-manager__stats">
        {documents.length} file{documents.length !== 1 ? 's' : ''} &middot; {formatSize(totalSize)} &middot; {indexedCount} indexed
        {searchQuery || filterType !== 'all' ? ` · ${filteredDocs.length} shown` : ''}
      </div>

      {documents.length === 0 ? (
        <div className="file-manager__empty">
          <div className="icon">📂</div>
          <div className="title">No files yet</div>
          <div className="hint">Drag and drop files anywhere on the desktop to upload them</div>
        </div>
      ) : (
        <div className="file-manager__list">
          <div className="file-manager__header">
            <span></span>
            <span>Name</span>
            <span>Status</span>
            <span>Size</span>
            <span>Uploaded</span>
            <span></span>
          </div>
          {filteredDocs.map(doc => {
            const status = getStatusLabel(doc.status);
            return (
              <div key={doc.id} className="file-item" title={doc.error_message || undefined}>
                <span className="file-item__icon">{getFileIcon(doc.file_type)}</span>
                <span className="file-item__name">{doc.filename}</span>
                <span className={`file-item__status file-item__status--${doc.status}`}>
                  {doc.status === 'processing' ? <span className="processing-spinner" /> : status.icon}
                  {' '}{status.label}
                  {doc.status === 'indexed' && doc.chunk_count > 0 && ` (${doc.chunk_count})`}
                </span>
                <span className="file-item__size">{formatSize(doc.file_size)}</span>
                <span className="file-item__time">{formatTime(doc.upload_time)}</span>
                <button
                  className="file-item__delete"
                  onClick={() => handleDelete(doc.id, doc.filename)}
                  title="Delete file and remove from index"
                >
                  ✕
                </button>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
