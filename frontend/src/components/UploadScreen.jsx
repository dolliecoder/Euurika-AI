import { useState, useCallback } from 'react';
import styles from './UploadScreen.module.css';

export function UploadScreen({ onUploadComplete, onBack }) {
  const [isDragging, setIsDragging] = useState(false);
  const [files, setFiles] = useState([]);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [error, setError] = useState(null);

  const handleDragOver = useCallback((e) => {
    e.preventDefault();
    setIsDragging(true);
  }, []);

  const handleDragLeave = useCallback((e) => {
    e.preventDefault();
    setIsDragging(false);
  }, []);

  const handleDrop = useCallback((e) => {
    e.preventDefault();
    setIsDragging(false);
    const droppedFiles = Array.from(e.dataTransfer.files);
    setFiles(prev => [...prev, ...droppedFiles]);
  }, []);

  const handleFileSelect = useCallback((e) => {
    const selectedFiles = Array.from(e.target.files);
    setFiles(prev => [...prev, ...selectedFiles]);
  }, []);

  const removeFile = useCallback((index) => {
    setFiles(prev => prev.filter((_, i) => i !== index));
  }, []);

  const handleUpload = async () => {
    if (files.length === 0) return;
    
    setIsUploading(true);
    setUploadProgress(0);
    setError(null);

    const formData = new FormData();
    files.forEach(file => {
      formData.append('files', file);
    });

    try {
      const response = await fetch('http://localhost:8001/upload', {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Upload failed');
      }

      const result = await response.json();
      setUploadProgress(100);
      
      // Small delay to show completion
      setTimeout(() => {
        onUploadComplete(result.session_id, result.files_processed);
      }, 500);
    } catch (e) {
      setError(e.message);
    } finally {
      setIsUploading(false);
    }
  };

  const formatFileSize = (bytes) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  return (
    <div className={styles.container}>
      <div className={styles.header}>
        <button className={styles.backBtn} onClick={onBack}>
          <BackIcon />
          <span>Back</span>
        </button>
        <h1>Upload Documents</h1>
        <p className={styles.subtitle}>
          Add your FAQ documents for Eurika to learn from
        </p>
      </div>

      <div className={styles.content}>
        {/* Drop Zone */}
        <div
          className={`${styles.dropZone} ${isDragging ? styles.dragging : ''}`}
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
          onClick={() => document.getElementById('fileInput').click()}
        >
          <input
            type="file"
            id="fileInput"
            multiple
            accept=".pdf,.md,.txt,.doc,.docx"
            onChange={handleFileSelect}
            className={styles.hiddenInput}
          />
          
          <div className={styles.dropIcon}>
            <UploadIcon />
          </div>
          
          <div className={styles.dropText}>
            <span className={styles.dropPrimary}>
              Drop files here or click to browse
            </span>
            <span className={styles.dropSecondary}>
              PDF, Markdown, TXT, DOCX supported
            </span>
          </div>
        </div>

        {/* File List */}
        {files.length > 0 && (
          <div className={styles.fileList}>
            <div className={styles.fileListHeader}>
              <span>{files.length} file{files.length !== 1 ? 's' : ''} selected</span>
              <button 
                className={styles.clearBtn}
                onClick={() => setFiles([])}
              >
                Clear all
              </button>
            </div>
            
            <div className={styles.files}>
              {files.map((file, index) => (
                <div key={index} className={styles.fileItem}>
                  <div className={styles.fileIcon}>
                    <FileIcon />
                  </div>
                  <div className={styles.fileInfo}>
                    <span className={styles.fileName}>{file.name}</span>
                    <span className={styles.fileSize}>{formatFileSize(file.size)}</span>
                  </div>
                  <button 
                    className={styles.removeBtn}
                    onClick={() => removeFile(index)}
                    disabled={isUploading}
                  >
                    <CloseIcon />
                  </button>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Error */}
        {error && (
          <div className={styles.error}>
            <ErrorIcon />
            <span>{error}</span>
          </div>
        )}

        {/* Upload Button */}
        <div className={styles.actions}>
          <button
            className={styles.uploadBtn}
            onClick={handleUpload}
            disabled={files.length === 0 || isUploading}
          >
            {isUploading ? (
              <>
                <div className={styles.spinner} />
                <span>Uploading... {uploadProgress}%</span>
              </>
            ) : (
              <>
                <UploadIcon />
                <span>Upload & Process</span>
              </>
            )}
          </button>
        </div>

        {/* Info */}
        <div className={styles.info}>
          <InfoIcon />
          <p>
            Your documents are processed locally and used only to answer your questions.
            All processing happens on your server.
          </p>
        </div>
      </div>
    </div>
  );
}

export function UploadIcon() {
  return (
    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
      <polyline points="17 8 12 3 7 8" />
      <line x1="12" y1="3" x2="12" y2="15" />
    </svg>
  );
}

export function BackIcon() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <line x1="19" y1="12" x2="5" y2="12" />
      <polyline points="12 19 5 12 12 5" />
    </svg>
  );
}

export function FileIcon() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
      <polyline points="14 2 14 8 20 8" />
      <line x1="16" y1="13" x2="8" y2="13" />
      <line x1="16" y1="17" x2="8" y2="17" />
    </svg>
  );
}

export function CloseIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <line x1="18" y1="6" x2="6" y2="18" />
      <line x1="6" y1="6" x2="18" y2="18" />
    </svg>
  );
}

export function ErrorIcon() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <circle cx="12" cy="12" r="10" />
      <line x1="15" y1="9" x2="9" y2="15" />
      <line x1="9" y1="9" x2="15" y2="15" />
    </svg>
  );
}

export function InfoIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <circle cx="12" cy="12" r="10" />
      <line x1="12" y1="16" x2="12" y2="12" />
      <line x1="12" y1="8" x2="12.01" y2="8" />
    </svg>
  );
}