import React, { useState, useEffect } from 'react';
import { api } from './api';
import NetworkCanvas from './components/NetworkCanvas';
import PropertiesPanel from './components/PropertiesPanel';
import ElementPalette from './components/ElementPalette';
import SimulationResults from './components/SimulationResults';

export default function App() {
  const [network, setNetwork] = useState({ nodes: [], connections: [] });
  const [report, setReport] = useState({});
  const [history, setHistory] = useState([]);
  const [selectedItem, setSelectedItem] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  // Modal dialog state: null, 'node', 'connection'
  const [modalMode, setModalMode] = useState(null);

  const loadNetwork = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await api.getNetwork();
      setNetwork(data.network || { nodes: [], connections: [] });
      setReport(data.report || {});
      setHistory(data.history || []);

      // Keep selected item reference up to date
      if (selectedItem) {
        if (selectedItem.type === 'node') {
          const updated = data.network.nodes.find((n) => n.id === selectedItem.id);
          setSelectedItem(updated ? { type: 'node', id: updated.id, item: updated } : null);
        } else {
          const updated = data.network.connections.find((c) => c.id === selectedItem.id);
          setSelectedItem(updated ? { type: 'connection', id: updated.id, item: updated } : null);
        }
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadNetwork();
  }, []);

  // Handlers for node/connection mutations
  const handleAddNode = async (nodeData) => {
    try {
      setError(null);
      await api.addElement(nodeData);
      await loadNetwork();
    } catch (err) {
      setError(err.message);
    }
  };

  const handleUpdateNode = async (id, updates) => {
    try {
      setError(null);
      await api.updateElement(id, updates);
      await loadNetwork();
    } catch (err) {
      setError(err.message);
    }
  };

  const handleDeleteNode = async (id) => {
    try {
      setError(null);
      await api.deleteElement(id);
      setSelectedItem(null);
      await loadNetwork();
    } catch (err) {
      setError(err.message);
    }
  };

  const handleMoveNode = async (id, x, y) => {
    try {
      await api.updateElement(id, { x, y });
    } catch (err) {
      console.error('Failed to persist node position:', err);
    }
  };

  const handleAddConnection = async (connData) => {
    try {
      setError(null);
      await api.addConnection(connData);
      await loadNetwork();
    } catch (err) {
      setError(err.message);
    }
  };

  const handleUpdateConnection = async (id, updates) => {
    try {
      setError(null);
      await api.updateConnection(id, updates);
      await loadNetwork();
    } catch (err) {
      setError(err.message);
    }
  };

  const handleDeleteConnection = async (id) => {
    try {
      setError(null);
      await api.deleteConnection(id);
      setSelectedItem(null);
      await loadNetwork();
    } catch (err) {
      setError(err.message);
    }
  };

  const handleToggleFailure = async (id, type, isFailed) => {
    try {
      setError(null);
      if (isFailed) {
        await api.triggerRestore(id, type);
      } else {
        await api.triggerFailure(id, type);
      }
      await loadNetwork();
    } catch (err) {
      setError(err.message);
    }
  };

  const handleOptimize = async () => {
    try {
      setError(null);
      await api.optimize();
      await loadNetwork();
    } catch (err) {
      setError(err.message);
    }
  };

  const handleReset = async () => {
    try {
      setError(null);
      setSelectedItem(null);
      await api.reset();
      await loadNetwork();
    } catch (err) {
      setError(err.message);
    }
  };

  // Derive honest overall network status
  const totalDemand = report.total_demand ?? 0;
  const totalSupplied = report.total_supplied ?? 0;
  const totalUnmet = report.total_unmet ?? 0;
  const failedComponents = report.failed_components || [];

  let overallStatus = 'NORMAL';
  if (totalDemand > 0 && totalSupplied === 0) {
    overallStatus = 'FAILED';
  } else if (failedComponents.length > 0) {
    if (totalUnmet > 0) {
      overallStatus = 'PARTIAL RECOVERY';
    } else {
      overallStatus = 'OPTIMIZED';
    }
  } else if (totalUnmet > 0) {
    overallStatus = 'UNSERVED';
  } else {
    overallStatus = 'NORMAL';
  }

  const statusClass =
    overallStatus === 'NORMAL'
      ? 'normal'
      : overallStatus === 'OPTIMIZED'
      ? 'optimized'
      : overallStatus === 'PARTIAL RECOVERY'
      ? 'partial'
      : 'failed';

  return (
    <div className="app-layout">
      {/* Top Toolbar */}
      <header className="top-toolbar">
        <div className="toolbar-brand">
          <span className="toolbar-title">Power Grid Simulator</span>
          <div className="toolbar-divider" />
          <span className={`status-indicator ${statusClass}`}>
            STATUS: {overallStatus}
          </span>
        </div>

        <div className="toolbar-actions">
          {/* Quick failure/restore button for selected item */}
          {selectedItem && (
            <div className="toolbar-selection-actions">
              <button
                className={`btn ${selectedItem.item.status === 'failed' ? 'btn-success' : 'btn-danger'}`}
                onClick={() =>
                  handleToggleFailure(
                    selectedItem.id,
                    selectedItem.type,
                    selectedItem.item.status === 'failed'
                  )
                }
              >
                {selectedItem.item.status === 'failed'
                  ? `Restore ${selectedItem.id}`
                  : `Simulate Failure (${selectedItem.id})`}
              </button>
              <div className="toolbar-divider" />
            </div>
          )}

          <button className="btn" onClick={() => setModalMode('node')}>
            + Add Element
          </button>
          <button className="btn" onClick={() => setModalMode('connection')}>
            + Add Connection
          </button>
          <button className="btn btn-primary" onClick={handleOptimize} disabled={loading}>
            Optimize
          </button>
          <button className="btn" onClick={handleReset} disabled={loading}>
            Reset
          </button>
        </div>
      </header>

      {/* Global Error Alert */}
      {error && (
        <div className="alert-strip">
          <span>Error: {error}</span>
          <button onClick={() => setError(null)}>✕</button>
        </div>
      )}

      {/* Main Workspace */}
      <div className="main-workspace">
        {/* Central Network Canvas Area */}
        <section className="canvas-section">
          <div className="canvas-header-bar">
            <div className="legend-bar">
              <span className="legend-chip">
                <span className="legend-color" style={{ background: '#1d4ed8' }} /> Generator
              </span>
              <span className="legend-chip">
                <span className="legend-color" style={{ background: '#0f766e' }} /> Transformer
              </span>
              <span className="legend-chip">
                <span className="legend-color" style={{ background: '#b91c1c' }} /> Hospital [P1]
              </span>
              <span className="legend-chip">
                <span className="legend-color" style={{ background: '#6d28d9' }} /> Factory [P2]
              </span>
              <span className="legend-chip">
                <span className="legend-color" style={{ background: '#b45309' }} /> School [P3]
              </span>
              <span className="legend-chip">
                <span className="legend-color" style={{ background: '#475569' }} /> House [P4]
              </span>
            </div>
            <span>Drag nodes to reposition • Click to inspect • Double-click node to toggle failure</span>
          </div>

          <NetworkCanvas
            nodes={network.nodes}
            connections={network.connections}
            selectedItem={selectedItem}
            onSelectItem={setSelectedItem}
            onMoveNode={handleMoveNode}
            onToggleFailure={handleToggleFailure}
          />
        </section>

        {/* Right Sidebar: Properties Inspector & Simulation Results */}
        <aside className="sidebar-panel">
          <PropertiesPanel
            selectedItem={selectedItem}
            onUpdateNode={handleUpdateNode}
            onUpdateConnection={handleUpdateConnection}
            onDeleteNode={handleDeleteNode}
            onDeleteConnection={handleDeleteConnection}
            onToggleFailure={handleToggleFailure}
          />

          <SimulationResults
            report={report}
            nodes={network.nodes}
            history={history}
          />
        </aside>
      </div>

      {/* Add Element / Connection Modal */}
      <ElementPalette
        isOpen={modalMode !== null}
        mode={modalMode}
        onClose={() => setModalMode(null)}
        nodes={network.nodes}
        onAddNode={handleAddNode}
        onAddConnection={handleAddConnection}
      />
    </div>
  );
}
