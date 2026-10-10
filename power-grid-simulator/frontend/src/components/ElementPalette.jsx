import React, { useState } from 'react';

export default function ElementPalette({
  isOpen,
  mode,
  onClose,
  nodes = [],
  onAddNode,
  onAddConnection
}) {
  // Node state
  const [nodeId, setNodeId] = useState('');
  const [nodeName, setNodeName] = useState('');
  const [nodeType, setNodeType] = useState('generator');
  const [capacity, setCapacity] = useState('50');
  const [demand, setDemand] = useState('20');
  const [priority, setPriority] = useState('1');

  // Connection state
  const [connId, setConnId] = useState('');
  const [source, setSource] = useState('');
  const [destination, setDestination] = useState('');
  const [connCap, setConnCap] = useState('30');
  const [connCost, setConnCost] = useState('50');

  if (!isOpen) return null;

  const isConsumer = ['hospital', 'factory', 'school', 'house'].includes(nodeType);

  const handleNodeSubmit = (e) => {
    e.preventDefault();
    if (!nodeId.trim()) return;

    onAddNode({
      id: nodeId.trim(),
      name: nodeName.trim() || nodeId.trim(),
      type: nodeType,
      capacity: !isConsumer ? parseFloat(capacity) || 0 : 0,
      demand: isConsumer ? parseFloat(demand) || 0 : 0,
      priority: isConsumer ? parseInt(priority, 10) : null,
      x: 200 + Math.floor(Math.random() * 250),
      y: 150 + Math.floor(Math.random() * 250)
    });

    setNodeId('');
    setNodeName('');
    onClose();
  };

  const handleConnectionSubmit = (e) => {
    e.preventDefault();
    if (!connId.trim() || !source || !destination) return;

    onAddConnection({
      id: connId.trim(),
      source,
      destination,
      capacity: parseFloat(connCap) || 0,
      cost: parseFloat(connCost) || 0
    });

    setConnId('');
    onClose();
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-dialog" onClick={(e) => e.stopPropagation()}>
        {mode === 'node' ? (
          <form onSubmit={handleNodeSubmit}>
            <div className="modal-header">
              <span className="modal-title">Add Network Element</span>
              <button type="button" className="btn" onClick={onClose} style={{ height: '22px', padding: '0 6px' }}>
                ✕
              </button>
            </div>

            <div className="modal-body">
              <div className="form-field">
                <label className="form-label">Element Type</label>
                <select
                  className="form-select"
                  value={nodeType}
                  onChange={(e) => {
                    const t = e.target.value;
                    setNodeType(t);
                    if (t === 'hospital') setPriority('1');
                    else if (t === 'factory') setPriority('2');
                    else if (t === 'school') setPriority('3');
                    else if (t === 'house') setPriority('4');
                  }}
                >
                  <option value="generator">Generator (Power Source)</option>
                  <option value="transformer">Transformer (Substation)</option>
                  <option value="hospital">Hospital (Consumer - Priority 1)</option>
                  <option value="factory">Factory (Consumer - Priority 2)</option>
                  <option value="school">School (Consumer - Priority 3)</option>
                  <option value="house">House (Consumer - Priority 4)</option>
                </select>
              </div>

              <div className="form-row">
                <div className="form-field">
                  <label className="form-label">Element ID</label>
                  <input
                    className="form-input"
                    type="text"
                    placeholder="e.g. G3, H2"
                    value={nodeId}
                    onChange={(e) => setNodeId(e.target.value)}
                    required
                  />
                </div>
                <div className="form-field">
                  <label className="form-label">Display Name</label>
                  <input
                    className="form-input"
                    type="text"
                    placeholder="Name"
                    value={nodeName}
                    onChange={(e) => setNodeName(e.target.value)}
                  />
                </div>
              </div>

              {isConsumer ? (
                <div className="form-row">
                  <div className="form-field">
                    <label className="form-label">Demand (kW)</label>
                    <input
                      className="form-input"
                      type="number"
                      min="0"
                      step="any"
                      value={demand}
                      onChange={(e) => setDemand(e.target.value)}
                      required
                    />
                  </div>
                  <div className="form-field">
                    <label className="form-label">Service Priority (1 = High)</label>
                    <input
                      className="form-input"
                      type="number"
                      min="1"
                      value={priority}
                      onChange={(e) => setPriority(e.target.value)}
                      required
                    />
                  </div>
                </div>
              ) : (
                <div className="form-field">
                  <label className="form-label">
                    {nodeType === 'generator' ? 'Max Generation Capacity' : 'Max Throughput Capacity'}
                  </label>
                  <input
                    className="form-input"
                    type="number"
                    min="0"
                    step="any"
                    value={capacity}
                    onChange={(e) => setCapacity(e.target.value)}
                    required
                  />
                </div>
              )}
            </div>

            <div className="modal-footer">
              <button type="button" className="btn" onClick={onClose}>
                Cancel
              </button>
              <button type="submit" className="btn btn-primary">
                Add Element
              </button>
            </div>
          </form>
        ) : (
          <form onSubmit={handleConnectionSubmit}>
            <div className="modal-header">
              <span className="modal-title">Add Directed Connection</span>
              <button type="button" className="btn" onClick={onClose} style={{ height: '22px', padding: '0 6px' }}>
                ✕
              </button>
            </div>

            <div className="modal-body">
              <div className="form-field">
                <label className="form-label">Connection ID</label>
                <input
                  className="form-input"
                  type="text"
                  placeholder="e.g. C12"
                  value={connId}
                  onChange={(e) => setConnId(e.target.value)}
                  required
                />
              </div>

              <div className="form-row">
                <div className="form-field">
                  <label className="form-label">Source Node (A)</label>
                  <select
                    className="form-select"
                    value={source}
                    onChange={(e) => setSource(e.target.value)}
                    required
                  >
                    <option value="">Select Source</option>
                    {nodes.map((n) => (
                      <option key={n.id} value={n.id}>
                        {n.id} ({n.name})
                      </option>
                    ))}
                  </select>
                </div>
                <div className="form-field">
                  <label className="form-label">Destination Node (B)</label>
                  <select
                    className="form-select"
                    value={destination}
                    onChange={(e) => setDestination(e.target.value)}
                    required
                  >
                    <option value="">Select Destination</option>
                    {nodes.map((n) => (
                      <option key={n.id} value={n.id}>
                        {n.id} ({n.name})
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              <div className="form-row">
                <div className="form-field">
                  <label className="form-label">Max Transmission Capacity</label>
                  <input
                    className="form-input"
                    type="number"
                    min="0"
                    step="any"
                    value={connCap}
                    onChange={(e) => setConnCap(e.target.value)}
                    required
                  />
                </div>
                <div className="form-field">
                  <label className="form-label">Installation Cost ($)</label>
                  <input
                    className="form-input"
                    type="number"
                    min="0"
                    step="any"
                    value={connCost}
                    onChange={(e) => setConnCost(e.target.value)}
                    required
                  />
                </div>
              </div>
            </div>

            <div className="modal-footer">
              <button type="button" className="btn" onClick={onClose}>
                Cancel
              </button>
              <button type="submit" className="btn btn-primary">
                Add Connection
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  );
}
