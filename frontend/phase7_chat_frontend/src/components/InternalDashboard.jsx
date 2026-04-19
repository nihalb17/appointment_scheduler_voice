import { useState, useEffect, useCallback } from "react";
import {
  listKnowledgeBaseFiles,
  uploadFile,
  deleteFile,
  getDownloadUrl,
} from "../services/api";
import "./InternalDashboard.css";

export default function InternalDashboard() {
  const [files, setFiles] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [uploadStatus, setUploadStatus] = useState(null);

  const loadFiles = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await listKnowledgeBaseFiles();
      setFiles(data.files);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadFiles();
  }, [loadFiles]);

  const handleFileChange = async (e) => {
    const file = e.target.files[0];
    if (!file) return;

    try {
      setUploadStatus({ type: "loading", message: `Uploading ${file.name}...` });
      await uploadFile(file);
      setUploadStatus({ type: "success", message: `${file.name} uploaded successfully!` });
      loadFiles(); // Refresh file list
      
      // Clear status after 3 seconds
      setTimeout(() => setUploadStatus(null), 3000);
    } catch (err) {
      setUploadStatus({ type: "error", message: err.message });
    }

    // Reset file input
    e.target.value = "";
  };

  const handleDownload = (filename) => {
    const url = getDownloadUrl(filename);
    window.open(url, "_blank");
  };

  const handleDelete = async (filename) => {
    if (!confirm(`Are you sure you want to delete "${filename}"?`)) {
      return;
    }

    try {
      await deleteFile(filename);
      loadFiles(); // Refresh file list
    } catch (err) {
      setError(err.message);
    }
  };

  const getFileIcon = (extension) => {
    const ext = extension.replace(".", "").toUpperCase();
    if (ext === "PDF") return "PDF";
    if (ext === "CSV") return "CSV";
    if (ext === "XLSX") return "XLS";
    if (ext === "DOCX") return "DOC";
    if (ext === "TXT") return "TXT";
    return ext.slice(0, 3);
  };

  const formatDate = (timestamp) => {
    return new Date(timestamp * 1000).toLocaleString();
  };

  return (
    <div className="internal-dashboard">
      <h1>Internal Dashboard</h1>
      <p className="subtitle">Manage knowledge base files for the Eligibility Agent</p>

      {error && (
        <div className="error-message">
          Error: {error}
          <button onClick={() => setError(null)} style={{ marginLeft: "10px" }}>
            Dismiss
          </button>
        </div>
      )}

      <div className="upload-section">
        <h3>Upload File</h3>
        <p className="supported-formats">
          Supported formats: PDF, CSV, XLSX, DOCX, TXT (max 10MB)
        </p>
        <div className="upload-area">
          <input
            type="file"
            id="file-upload"
            accept=".pdf,.csv,.xlsx,.docx,.txt"
            onChange={handleFileChange}
          />
          <label htmlFor="file-upload" className="upload-button">
            Choose File
          </label>
          <p style={{ marginTop: "12px", color: "#666" }}>
            or drag and drop files here
          </p>
        </div>
        {uploadStatus && (
          <div className={`upload-status ${uploadStatus.type}`}>
            {uploadStatus.message}
          </div>
        )}
      </div>

      <div className="files-section">
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <h3>Knowledge Base Files ({files.length})</h3>
          <button className="refresh-btn" onClick={loadFiles} disabled={loading}>
            {loading ? "Loading..." : "Refresh"}
          </button>
        </div>

        {loading ? (
          <div className="loading">Loading files...</div>
        ) : files.length === 0 ? (
          <div className="no-files">
            <p>No files in the knowledge base yet.</p>
            <p>Upload files above to get started.</p>
          </div>
        ) : (
          <div className="files-list">
            {files.map((file) => (
              <div key={file.name} className="file-item">
                <div className="file-icon">{getFileIcon(file.extension)}</div>
                <div className="file-info">
                  <div className="file-name">{file.name}</div>
                  <div className="file-meta">
                    {file.size_human} • Modified: {formatDate(file.modified)}
                  </div>
                </div>
                <div className="file-actions">
                  <button
                    className="download-btn"
                    onClick={() => handleDownload(file.name)}
                  >
                    Download
                  </button>
                  <button
                    className="delete-btn"
                    onClick={() => handleDelete(file.name)}
                  >
                    Delete
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
