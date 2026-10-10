import React, { useState, useEffect } from 'react';

export default function PropertiesPanel({
  selectedItem,
  onUpdateNode,
  onUpdateConnection,
  onDeleteNode,
  onDeleteConnection,
  onToggleFailure
}) {
  const [fields, setFields] = useState({});

  useEffect(() => {
    if (selectedItem?.item) {
      setFields({ ...selectedItem.item });
    } else {
      setFields({});
    }
  }, [selectedItem]);

  if (!selectedItem || !selectedItem.item) {
    return (
      <div className="panel-block">
        <div className="panel-title">Properties Inspector</div>
        <div className="empty-inspector">
          Select any node or connection on the canvas to inspect and edit properties or simulate component failure.
        </div>
      </div>
    );
  }

  const { type, item } = selectedItem;
  const isNode = type === 'node';
  const isConsumer = isNode && ['hospital', 'factory', 'school', 'house'].includes(item.type);
  const isFailed = item.status === 'failed';

  const handleSubmit = (e) => {
    e.preventDefault();
    if (isNode) {
      onUpdateNode(item.id, {
        name: fields.name,
        capacity: parseFloat(fields.capacity) || 0,
        demand: parseFloat(fields.demand) || 0,
        priority: fields.priority ? parseInt(fields.priority, 10) : undefined
      });
    } else {
      onUpdateConnection(item.id, {
        capacity: parseFloat(fields.capacity) || 0,
        cost: parseFloat(fields.cost) || 0
      });
    }
  };

  return (
    <div className="panel-block">
      <div className="panel-title">
        <span>{isNode ? `Node: ${item.id}` : `Connection: ${item.id}`}</span>
        <span className={`status-indicator ${isFailed ? 'failed' : 'normal'}`}>
          {isFailed ? 'FAILED' : 'ACTIVE'}
        </span>
      </div>

      <form onSubmit={handleSubmit}>
        {isNode ? (
          <>
            <div className="form-field">
              <label className="form-label">Name</label>
              <input
                className="form-input"
                type="text"
                value={fields.name || ''}
                onChange={(e) => setFields({ ...fields, name: e.target.value })}
                required
              />
            </div>

            <div className="form-row">
              <div className="form-field">
                <label className="form-label">Type</label>
                <input
                  className="form-input"
                  type="text"
                  value={item.type.toUpperCase()}
                  disabled
                />
              </div>
              <div className="form-field">
                <label className="form-label">Node ID</label>
                <input className="form-input" type="text" value={item.id} disabled />
              </div>
            </div>

            {isConsumer ? (
              <>
                <div className="form-row">
                  <div className="form-field">
                    <label className="form-label">Demand (kW)</label>
                    <input
                      className="form-input"
                      type="number"
                      min="0"
                      step="any"
                      value={fields.demand ?? 0}
                      onChange={(e) => setFields({ ...fields, demand: e.target.value })}
                      required
                    />
                  </div>
                  <div className="form-field">
                    <label className="form-label">Priority (1 = High)</label>
                    <input
                      className="form-input"
                      type="number"
                      min="1"
                      value={fields.priority ?? 4}
                      onChange={(e) => setFields({ ...fields, priority: e.target.value })}
                      required
                    />
                  </div>
                </div>

                <div className="form-row">
                  <div className="form-field">
                    <label className="form-label">Supplied (Calculated)</label>
                    <input
                      className="form-input"
                      type="text"
                      value={`${item.supplied} kW`}
                      disabled
                    />
                  </div>
                  <div className="form-field">
                    <label className="form-label">Unmet Deficit</label>
                    <input
                      className="form-input"
                      type="text"
                      value={`${item.unmet_demand} kW`}
                      disabled
                    />
                  </div>
                </div>
              </>
            ) : (
              <div className="form-field">
                <label className="form-label">
                  {item.type === 'generator' ? 'Max Generation Capacity' : 'Max Throughput Capacity'}
                </label>
                <input
                  className="form-input"
                  type="number"
                  min="0"
                  step="any"
                  value={fields.capacity ?? 0}
                  onChange={(e) => setFields({ ...fields, capacity: e.target.value })}
                  required
                />
              </div>
            )}
          </>
        ) : (
          <>
            <div className="form-row">
              <div className="form-field">
                <label className="form-label">Source Node</label>
                <input className="form-input" type="text" value={item.source} disabled />
              </div>
              <div className="form-field">
                <label className="form-label">Destination Node</label>
                <input className="form-input" type="text" value={item.destination} disabled />
              </div>
            </div>

            <div className="form-row">
              <div className="form-field">
                <label className="form-label">Transmission Capacity</label>
                <input
                  className="form-input"
                  type="number"
                  min="0"
                  step="any"
                  value={fields.capacity ?? 0}
                  onChange={(e) => setFields({ ...fields, capacity: e.target.value })}
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
                  value={fields.cost ?? 0}
                  onChange={(e) => setFields({ ...fields, cost: e.target.value })}
                  required
                />
              </div>
            </div>

            <div className="form-field">
              <label className="form-label">Allocated Flow (Calculated)</label>
              <input
                className="form-input"
                type="text"
                value={`${item.flow} / ${item.capacity} kW`}
                disabled
              />
            </div>
          </>
        )}

        <div className="inspector-actions">
          <button type="submit" className="btn btn-primary">
            Apply Changes
          </button>
          <button
            type="button"
            className={`btn ${isFailed ? 'btn-success' : 'btn-danger'}`}
            onClick={() => onToggleFailure(item.id, isNode ? 'node' : 'connection', isFailed)}
          >
            {isFailed ? 'Restore Component' : 'Simulate Failure'}
          </button>
          <button
            type="button"
            className="btn"
            onClick={() => {
              if (window.confirm(`Delete ${isNode ? 'node' : 'connection'} ${item.id}?`)) {
                if (isNode) onDeleteNode(item.id);
                else onDeleteConnection(item.id);
              }
            }}
          >
            Delete
          </button>
        </div>
      </form>
    </div>
  );
}
