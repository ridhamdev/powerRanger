import React from 'react';

export default function SimulationResults({ report = {}, nodes = [], history = [] }) {
  const totalDemand = report.total_demand ?? 0;
  const totalSupplied = report.total_supplied ?? 0;
  const totalUnmet = report.total_unmet ?? 0;
  const cost = report.installation_cost ?? 0;

  const fullSupply = report.full_supply_consumers || [];
  const partialSupply = report.partial_supply_consumers || [];
  const noSupply = report.no_supply_consumers || [];
  const bottlenecks = report.bottlenecks || [];
  const failedComponents = report.failed_components || [];

  // Determine overall recovery status honestly
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

  // Consumers list sorted by priority rank
  const consumers = nodes
    .filter((n) => ['hospital', 'factory', 'school', 'house'].includes(n.type))
    .sort((a, b) => (a.priority || 99) - (b.priority || 99));

  const lastEvent = history.length > 0 ? history[history.length - 1] : null;

  return (
    <div className="panel-block">
      <div className="panel-title">
        <span>Simulation Results</span>
        <span className={`status-indicator ${statusClass}`}>{overallStatus}</span>
      </div>

      {/* Aggregate Telemetry Metrics */}
      <table className="metrics-table">
        <tbody>
          <tr>
            <td className="metric-name">Total Demand</td>
            <td className="metric-value">{totalDemand.toFixed(1)} kW</td>
          </tr>
          <tr>
            <td className="metric-name">Total Supplied</td>
            <td className="metric-value" style={{ color: totalUnmet === 0 ? '#15803d' : '#b45309' }}>
              {totalSupplied.toFixed(1)} kW
            </td>
          </tr>
          <tr>
            <td className="metric-name">Total Unmet Deficit</td>
            <td className="metric-value" style={{ color: totalUnmet > 0 ? '#b91c1c' : '#64748b' }}>
              {totalUnmet.toFixed(1)} kW
            </td>
          </tr>
          <tr>
            <td className="metric-name">Installation Cost</td>
            <td className="metric-value">${cost.toFixed(1)}</td>
          </tr>
          <tr>
            <td className="metric-name">Fully Supplied Consumers</td>
            <td className="metric-value">{fullSupply.length}</td>
          </tr>
          <tr>
            <td className="metric-name">Partially Supplied Consumers</td>
            <td className="metric-value">{partialSupply.length}</td>
          </tr>
          <tr>
            <td className="metric-name">Unserved Consumers</td>
            <td className="metric-value">{noSupply.length}</td>
          </tr>
        </tbody>
      </table>

      {/* Consumer Priority Breakdown Table */}
      <div className="panel-title" style={{ marginTop: '12px', fontSize: '11px' }}>
        Consumer Priority Allocations
      </div>
      <table className="data-table">
        <thead>
          <tr>
            <th>Consumer</th>
            <th>Type</th>
            <th>Prio</th>
            <th>Demand</th>
            <th>Supply</th>
            <th>Status</th>
          </tr>
        </thead>
        <tbody>
          {consumers.length === 0 ? (
            <tr>
              <td colSpan="6" style={{ textAlign: 'center', color: '#64748b' }}>
                No consumers defined
              </td>
            </tr>
          ) : (
            consumers.map((c) => {
              const isFull = fullSupply.includes(c.id);
              const isPart = partialSupply.includes(c.id);
              const tagStatus = isFull ? 'full' : isPart ? 'partial' : 'none';
              const tagText = isFull ? 'FULL' : isPart ? 'PART' : 'NONE';

              return (
                <tr key={c.id}>
                  <td className="mono" title={c.name}>
                    <strong>{c.id}</strong>
                  </td>
                  <td>{c.type.slice(0, 4)}</td>
                  <td className="mono">P{c.priority}</td>
                  <td className="mono">{c.demand}</td>
                  <td className="mono">{c.supplied}</td>
                  <td>
                    <span className={`tag-badge ${tagStatus}`}>{tagText}</span>
                  </td>
                </tr>
              );
            })
          )}
        </tbody>
      </table>

      {/* Bottlenecks */}
      {bottlenecks.length > 0 && (
        <div style={{ marginTop: '12px' }}>
          <div className="panel-title" style={{ fontSize: '11px', color: '#b91c1c' }}>
            Capacity Bottlenecks
          </div>
          <ul className="bottleneck-list">
            {bottlenecks.map((b, i) => (
              <li key={i}>• {b}</li>
            ))}
          </ul>
        </div>
      )}

      {/* Latest Event Banner */}
      {lastEvent && (
        <div className="event-banner">
          <strong>Event #{lastEvent.step}:</strong> {lastEvent.message}
        </div>
      )}
    </div>
  );
}
