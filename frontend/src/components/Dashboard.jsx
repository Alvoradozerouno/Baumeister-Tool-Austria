import React, { useState, useEffect } from 'react';
import axios from 'axios';
import './Dashboard.css';

/**
 * ORION Architekt-AT Live Dashboard
 * ===================================
 * React component for:
 * - PDF/BIM file upload
 * - Real-time compliance checking
 * - 3D visualization
 * - Compliance report export
 * 
 * Author: ORION Swarm - Team B (Web UI)
 * Date: 2026-05-25
 */

const Dashboard = () => {
  // State management
  const [file, setFile] = useState(null);
  const [loading, setLoading] = useState(false);
  const [complianceResults, setComplianceResults] = useState(null);
  const [activeTab, setActiveTab] = useState('upload');
  const [visualizationMode, setVisualizationMode] = useState('2d'); // 2d, 3d, energy
  const [filters, setFilters] = useState({
    bundesland: 'wien',
    building_type: 'wohngebaeude',
    showWarnings: true,
  });

  // File upload handler
  const handleFileUpload = async (e) => {
    const selectedFile = e.target.files[0];
    if (!selectedFile) return;

    setFile(selectedFile);
    setLoading(true);

    try {
      const formData = new FormData();
      formData.append('file', selectedFile);
      formData.append('bundesland', filters.bundesland);
      formData.append('building_type', filters.building_type);

      // Determine endpoint based on file type
      let endpoint = '/api/v1/bim/upload-ifc';
      if (selectedFile.name.endsWith('.pdf')) {
        endpoint = '/api/v1/documents/analyze-pdf';
      }

      const response = await axios.post(endpoint, formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });

      setComplianceResults(response.data);
      setActiveTab('results');
    } catch (error) {
      console.error('Upload failed:', error);
      alert(`Upload failed: ${error.response?.data?.detail || error.message}`);
    } finally {
      setLoading(false);
    }
  };

  // Compliance check handler
  const handleComplianceCheck = async () => {
    if (!complianceResults) return;

    setLoading(true);
    try {
      const response = await axios.post('/api/v1/compliance/oib-rl-check', {
        bundesland: filters.bundesland,
        building_type: filters.building_type,
        bgf_m2: complianceResults.total_area_m2 || 1000,
        geschosse: complianceResults.stories || 3,
        wohnungen: complianceResults.units || 10,
      });

      setComplianceResults(prev => ({
        ...prev,
        compliance_checks: response.data,
      }));
    } catch (error) {
      console.error('Compliance check failed:', error);
    } finally {
      setLoading(false);
    }
  };

  // Export report as PDF
  const handleExportPDF = async () => {
    if (!complianceResults) return;

    try {
      const response = await axios.post(
        '/api/v1/reports/generate-pdf',
        complianceResults,
        { responseType: 'blob' }
      );

      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `compliance-report-${new Date().toISOString().split('T')[0]}.pdf`);
      document.body.appendChild(link);
      link.click();
    } catch (error) {
      console.error('PDF export failed:', error);
    }
  };

  return (
    <div className="dashboard-container">
      {/* Header */}
      <header className="dashboard-header">
        <div className="header-content">
          <h1>🏗️ ORION Architekt-AT</h1>
          <p>Compliance Dashboard | OIB-RL 2025 | Live Validation</p>
        </div>
        <div className="header-stats">
          <span>Status: <strong>🟢 LIVE</strong></span>
          <span>API: <strong>v1.0</strong></span>
          <span>Standard: <strong>OIB-RL 2025</strong></span>
        </div>
      </header>

      {/* Main Content */}
      <div className="dashboard-content">
        {/* Tab Navigation */}
        <div className="tab-navigation">
          <button
            className={`tab-btn ${activeTab === 'upload' ? 'active' : ''}`}
            onClick={() => setActiveTab('upload')}
          >
            📤 Upload & Analysis
          </button>
          <button
            className={`tab-btn ${activeTab === 'results' ? 'active' : ''}`}
            onClick={() => setActiveTab('results')}
            disabled={!complianceResults}
          >
            ✅ Compliance Results
          </button>
          <button
            className={`tab-btn ${activeTab === 'visualization' ? 'active' : ''}`}
            onClick={() => setActiveTab('visualization')}
            disabled={!complianceResults}
          >
            📊 Visualization
          </button>
        </div>

        {/* Tab Content */}
        <div className="tab-content">
          {/* Upload Tab */}
          {activeTab === 'upload' && (
            <div className="upload-section">
              <div className="filters">
                <div className="filter-group">
                  <label>Bundesland:</label>
                  <select
                    value={filters.bundesland}
                    onChange={(e) => setFilters({ ...filters, bundesland: e.target.value })}
                  >
                    <option value="wien">Wien</option>
                    <option value="niederösterreich">Niederösterreich</option>
                    <option value="oberösterreich">Oberösterreich</option>
                    <option value="salzburg">Salzburg</option>
                    <option value="tirol">Tirol</option>
                    <option value="vorarlberg">Vorarlberg</option>
                    <option value="steiermark">Steiermark</option>
                    <option value="kärnten">Kärnten</option>
                    <option value="burgenland">Burgenland</option>
                  </select>
                </div>

                <div className="filter-group">
                  <label>Building Type:</label>
                  <select
                    value={filters.building_type}
                    onChange={(e) => setFilters({ ...filters, building_type: e.target.value })}
                  >
                    <option value="wohngebaeude">Wohngebäude</option>
                    <option value="buerogebaeude">Bürogebäude</option>
                    <option value="industrie">Industrie</option>
                    <option value="einzelhandel">Einzelhandel</option>
                    <option value="schule">Schule</option>
                  </select>
                </div>

                <div className="filter-group">
                  <label>
                    <input
                      type="checkbox"
                      checked={filters.showWarnings}
                      onChange={(e) => setFilters({ ...filters, showWarnings: e.target.checked })}
                    />
                    Show Warnings
                  </label>
                </div>
              </div>

              <div className="upload-area">
                <div
                  className="upload-box"
                  onDragOver={(e) => e.preventDefault()}
                  onDrop={(e) => {
                    e.preventDefault();
                    handleFileUpload({ target: { files: e.dataTransfer.files } });
                  }}
                >
                  <input
                    type="file"
                    accept=".ifc,.pdf,.dwg"
                    onChange={handleFileUpload}
                    id="file-input"
                    style={{ display: 'none' }}
                  />
                  <label htmlFor="file-input" className="upload-label">
                    <span className="upload-icon">📁</span>
                    <h3>Drop files here or click to upload</h3>
                    <p>Supported: IFC, PDF, DWG</p>
                    {file && <p className="file-name">Selected: {file.name}</p>}
                  </label>
                </div>

                <button
                  className="btn btn-primary"
                  onClick={() => {
                    if (file) handleFileUpload({ target: { files: [file] } });
                  }}
                  disabled={!file || loading}
                >
                  {loading ? 'Processing...' : '🚀 Analyze'}
                </button>
              </div>

              <div className="quick-check">
                <h3>Or Quick-Check Parameters:</h3>
                <div className="quick-form">
                  <input type="number" placeholder="BGF (m²)" defaultValue="1000" />
                  <input type="number" placeholder="Stories" defaultValue="3" />
                  <input type="number" placeholder="Units" defaultValue="10" />
                  <button className="btn btn-secondary" onClick={handleComplianceCheck}>
                    Check Compliance
                  </button>
                </div>
              </div>
            </div>
          )}

          {/* Results Tab */}
          {activeTab === 'results' && complianceResults && (
            <div className="results-section">
              <div className="results-header">
                <h2>📋 Compliance Report</h2>
                <div className="result-stats">
                  <div className="stat">
                    <span className="label">Total Checks:</span>
                    <span className="value">{complianceResults.compliance_checks?.length || 0}</span>
                  </div>
                  <div className="stat">
                    <span className="label">Status:</span>
                    <span className={`value status-${complianceResults.overall_status || 'unknown'}`}>
                      {complianceResults.overall_status?.toUpperCase() || 'UNKNOWN'}
                    </span>
                  </div>
                  <div className="stat">
                    <span className="label">Building Area:</span>
                    <span className="value">{complianceResults.total_area_m2?.toFixed(0) || 'N/A'} m²</span>
                  </div>
                </div>
              </div>

              {/* Checks List */}
              <div className="checks-list">
                {complianceResults.compliance_checks?.map((check, idx) => (
                  <div
                    key={idx}
                    className={`check-item status-${check.status || 'info'}`}
                  >
                    <div className="check-header">
                      <span className="status-icon">
                        {check.status === 'pass' && '✅'}
                        {check.status === 'fail' && '❌'}
                        {check.status === 'warning' && '⚠️'}
                        {check.status === 'info' && 'ℹ️'}
                      </span>
                      <h4>{check.check_name || check.check || 'Unknown Check'}</h4>
                      <span className="category">{check.category || check.richtlinie || 'N/A'}</span>
                    </div>
                    <div className="check-details">
                      <p>{check.details}</p>
                      {check.relevant_standard && (
                        <p className="standard">Standard: {check.relevant_standard}</p>
                      )}
                      {check.affected_elements?.length > 0 && (
                        <p className="elements">Affected: {check.affected_elements.join(', ')}</p>
                      )}
                    </div>
                  </div>
                ))}
              </div>

              {/* Export Button */}
              <div className="results-footer">
                <button className="btn btn-primary" onClick={handleExportPDF}>
                  📥 Export as PDF
                </button>
                <button className="btn btn-secondary" onClick={() => setActiveTab('upload')}>
                  Upload Another File
                </button>
              </div>
            </div>
          )}

          {/* Visualization Tab */}
          {activeTab === 'visualization' && complianceResults && (
            <div className="visualization-section">
              <div className="viz-controls">
                <button
                  className={`viz-btn ${visualizationMode === '2d' ? 'active' : ''}`}
                  onClick={() => setVisualizationMode('2d')}
                >
                  📐 2D Plan
                </button>
                <button
                  className={`viz-btn ${visualizationMode === '3d' ? 'active' : ''}`}
                  onClick={() => setVisualizationMode('3d')}
                >
                  🎯 3D Model
                </button>
                <button
                  className={`viz-btn ${visualizationMode === 'energy' ? 'active' : ''}`}
                  onClick={() => setVisualizationMode('energy')}
                >
                  ⚡ Energy Analysis
                </button>
              </div>

              <div className="visualization-canvas" id="canvas-container">
                {visualizationMode === '2d' && (
                  <div className="placeholder">
                    <p>📐 2D Floorplan View (Three.js Canvas)</p>
                  </div>
                )}
                {visualizationMode === '3d' && (
                  <div className="placeholder">
                    <p>🎯 3D Building Model (Three.js Canvas)</p>
                  </div>
                )}
                {visualizationMode === 'energy' && (
                  <div className="placeholder">
                    <p>⚡ Energy Performance Analysis (Chart.js)</p>
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Footer */}
      <footer className="dashboard-footer">
        <p>🏗️ ORION Architekt-AT | OIB-RL 2025 | MIT License | © 2026</p>
        <p>
          <strong>⚠️ Disclaimer:</strong> This tool is a planning aid only. 
          Official submissions require certified Ziviltechniker signature.
        </p>
      </footer>
    </div>
  );
};

export default Dashboard;
