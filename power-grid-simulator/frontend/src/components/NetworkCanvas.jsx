import React, { useState, useEffect } from 'react';

const CATEGORY_COLORS = {
  generator: '#1d4ed8',   // Blue
  transformer: '#0f766e', // Teal
  hospital: '#b91c1c',    // Red
  factory: '#6d28d9',     // Purple
  school: '#b45309',      // Amber
  house: '#475569'        // Slate grey
};

const BLOCK_WIDTH = 146;
const BLOCK_HEIGHT = 60;
const HW = BLOCK_WIDTH / 2;
const HH = BLOCK_HEIGHT / 2;

export default function NetworkCanvas({
  nodes = [],
  connections = [],
  selectedItem = null,
  onSelectItem,
  onMoveNode,
  onToggleFailure
}) {
  const [dragState, setDragState] = useState(null);
  const [positions, setPositions] = useState({});

  // Sync positions from nodes prop
  useEffect(() => {
    const nextPos = {};
    nodes.forEach((n) => {
      nextPos[n.id] = { x: n.x, y: n.y };
    });
    setPositions(nextPos);
  }, [nodes]);

  // Drag handlers
  const handleNodeMouseDown = (nodeId, e) => {
    e.stopPropagation();
    const current = positions[nodeId] || { x: 0, y: 0 };
    setDragState({
      nodeId,
      startX: e.clientX,
      startY: e.clientY,
      nodeStartX: current.x,
      nodeStartY: current.y,
      moved: false
    });
  };

  const handleMouseMove = (e) => {
    if (!dragState) return;
    const dx = e.clientX - dragState.startX;
    const dy = e.clientY - dragState.startY;

    if (Math.abs(dx) > 3 || Math.abs(dy) > 3) {
      const nextX = Math.max(90, Math.min(1050, dragState.nodeStartX + dx));
      const nextY = Math.max(50, Math.min(680, dragState.nodeStartY + dy));

      setPositions((prev) => ({
        ...prev,
        [dragState.nodeId]: { x: nextX, y: nextY }
      }));
      dragState.moved = true;
    }
  };

  const handleMouseUp = () => {
    if (!dragState) return;
    if (dragState.moved) {
      const finalPos = positions[dragState.nodeId];
      if (finalPos && onMoveNode) {
        onMoveNode(dragState.nodeId, finalPos.x, finalPos.y);
      }
    } else {
      // Simple click -> select node
      const node = nodes.find((n) => n.id === dragState.nodeId);
      if (node) {
        onSelectItem({ type: 'node', id: node.id, item: node });
      }
    }
    setDragState(null);
  };

  // Canvas background click clears selection
  const handleCanvasClick = (e) => {
    if (e.target.tagName === 'svg' || e.target.classList.contains('canvas-container')) {
      onSelectItem(null);
    }
  };

  // Helper to compute orthogonal edge perimeter intersection
  const getEdgeEndpoints = (uPos, vPos) => {
    const dx = vPos.x - uPos.x;
    const dy = vPos.y - uPos.y;

    if (Math.abs(dx) * HH >= Math.abs(dy) * HW) {
      if (dx >= 0) {
        return {
          x1: uPos.x + HW,
          y1: uPos.y,
          x2: vPos.x - HW,
          y2: vPos.y
        };
      } else {
        return {
          x1: uPos.x - HW,
          y1: uPos.y,
          x2: vPos.x + HW,
          y2: vPos.y
        };
      }
    } else {
      if (dy >= 0) {
        return {
          x1: uPos.x,
          y1: uPos.y + HH,
          x2: vPos.x,
          y2: vPos.y - HH
        };
      } else {
        return {
          x1: uPos.x,
          y1: uPos.y - HH,
          x2: vPos.x,
          y2: vPos.y + HH
        };
      }
    }
  };

  return (
    <div
      className="canvas-container"
      onClick={handleCanvasClick}
      onMouseMove={handleMouseMove}
      onMouseUp={handleMouseUp}
      onMouseLeave={handleMouseUp}
    >
      <svg className="svg-canvas" viewBox="0 0 1100 720">
        <defs>
          {/* Arrowhead marker: Active carrying flow */}
          <marker
            id="arrow-flow"
            viewBox="0 0 10 10"
            refX="9"
            refY="5"
            markerWidth="7"
            markerHeight="7"
            orient="auto"
          >
            <path d="M 0 1.5 L 9 5 L 0 8.5 z" fill="#0f172a" />
          </marker>

          {/* Arrowhead marker: Zero flow active */}
          <marker
            id="arrow-idle"
            viewBox="0 0 10 10"
            refX="9"
            refY="5"
            markerWidth="7"
            markerHeight="7"
            orient="auto"
          >
            <path d="M 0 2 L 8 5 L 0 8 z" fill="#94a3b8" />
          </marker>

          {/* Arrowhead marker: Failed */}
          <marker
            id="arrow-failed"
            viewBox="0 0 10 10"
            refX="9"
            refY="5"
            markerWidth="7"
            markerHeight="7"
            orient="auto"
          >
            <path d="M 0 1.5 L 9 5 L 0 8.5 z" fill="#b91c1c" />
          </marker>

          {/* Arrowhead marker: Selected */}
          <marker
            id="arrow-selected"
            viewBox="0 0 10 10"
            refX="9"
            refY="5"
            markerWidth="7"
            markerHeight="7"
            orient="auto"
          >
            <path d="M 0 1.5 L 9 5 L 0 8.5 z" fill="#1d4ed8" />
          </marker>
        </defs>

        {/* Directed Connections */}
        {connections.map((conn) => {
          const uPos = positions[conn.source];
          const vPos = positions[conn.destination];
          if (!uPos || !vPos) return null;

          const pts = getEdgeEndpoints(uPos, vPos);
          const isSelected = selectedItem?.type === 'connection' && selectedItem?.id === conn.id;
          const isFailed = conn.status === 'failed';
          const hasFlow = conn.flow > 0;

          let stroke = hasFlow ? '#0f172a' : '#94a3b8';
          let strokeWidth = hasFlow ? 2 : 1.5;
          let marker = hasFlow ? 'url(#arrow-flow)' : 'url(#arrow-idle)';
          let strokeDash = 'none';

          if (isFailed) {
            stroke = '#b91c1c';
            strokeWidth = 1.75;
            marker = 'url(#arrow-failed)';
            strokeDash = '4,3';
          } else if (isSelected) {
            stroke = '#1d4ed8';
            strokeWidth = 2.5;
            marker = 'url(#arrow-selected)';
          }

          const midX = (pts.x1 + pts.x2) / 2;
          const midY = (pts.y1 + pts.y2) / 2;

          return (
            <g
              key={conn.id}
              className="svg-edge"
              onClick={(e) => {
                e.stopPropagation();
                onSelectItem({ type: 'connection', id: conn.id, item: conn });
              }}
            >
              {/* Transparent hit target */}
              <line
                x1={pts.x1}
                y1={pts.y1}
                x2={pts.x2}
                y2={pts.y2}
                stroke="transparent"
                strokeWidth="16"
              />

              {/* Visible connection line */}
              <line
                x1={pts.x1}
                y1={pts.y1}
                x2={pts.x2}
                y2={pts.y2}
                stroke={stroke}
                strokeWidth={strokeWidth}
                strokeDasharray={strokeDash}
                markerEnd={marker}
              />

              {/* Edge Metric Label Badge */}
              <g transform={`translate(${midX}, ${midY})`}>
                <rect
                  x="-28"
                  y="-10"
                  width="56"
                  height="20"
                  fill="#ffffff"
                  stroke={isSelected ? '#1d4ed8' : stroke}
                  strokeWidth="1"
                  rx="2"
                />
                <text
                  x="0"
                  y="4"
                  textAnchor="middle"
                  fontFamily="ui-monospace, monospace"
                  fontSize="10"
                  fontWeight={hasFlow ? '700' : '500'}
                  fill={isFailed ? '#b91c1c' : hasFlow ? '#0f172a' : '#64748b'}
                >
                  {isFailed ? 'FAILED' : `${conn.flow}/${conn.capacity}`}
                </text>
              </g>
            </g>
          );
        })}

        {/* Network Elements (Rectangular Blocks) */}
        {nodes.map((node) => {
          const pos = positions[node.id] || { x: node.x, y: node.y };
          const isSelected = selectedItem?.type === 'node' && selectedItem?.id === node.id;
          const isFailed = node.status === 'failed';
          const catColor = CATEGORY_COLORS[node.type] || '#475569';
          const isConsumer = ['hospital', 'factory', 'school', 'house'].includes(node.type);

          const left = pos.x - HW;
          const top = pos.y - HH;

          let blockFill = '#ffffff';
          let borderStroke = isSelected ? '#1d4ed8' : '#cbd5e1';
          let borderWidth = isSelected ? 2 : 1;
          let dashArray = 'none';

          if (isFailed) {
            blockFill = '#fef2f2';
            borderStroke = '#b91c1c';
            borderWidth = 1.75;
            dashArray = '4,3';
          }

          return (
            <g
              key={node.id}
              className="svg-node"
              transform={`translate(${left}, ${top})`}
              onMouseDown={(e) => handleNodeMouseDown(node.id, e)}
              onDoubleClick={(e) => {
                e.stopPropagation();
                onToggleFailure(node.id, 'node', isFailed);
              }}
            >
              {/* Outer Block Rectangle */}
              <rect
                className="svg-node-rect"
                x="0"
                y="0"
                width={BLOCK_WIDTH}
                height={BLOCK_HEIGHT}
                fill={blockFill}
                stroke={borderStroke}
                strokeWidth={borderWidth}
                strokeDasharray={dashArray}
                rx="3"
                ry="3"
              />

              {/* Top Category Color Bar */}
              <rect
                x="0"
                y="0"
                width={BLOCK_WIDTH}
                height="4"
                fill={catColor}
                rx="3"
                ry="3"
              />

              {/* Line 1: Node ID & Name */}
              <text
                x="8"
                y="19"
                fontSize="11"
                fontWeight="700"
                fontFamily="ui-monospace, monospace"
                fill="#0f172a"
              >
                {node.id}
              </text>
              <text
                x="32"
                y="19"
                fontSize="11"
                fontWeight="600"
                fill="#334155"
              >
                {node.name.length > 15 ? `${node.name.slice(0, 14)}…` : node.name}
              </text>

              {/* Line 2: Type & Priority */}
              <text
                x="8"
                y="34"
                fontSize="10"
                fill="#64748b"
                textTransform="uppercase"
              >
                {isConsumer ? `${node.type} [P${node.priority}]` : node.type}
              </text>

              {/* Line 3: Metric (Capacity or Demand/Supplied) */}
              {isFailed ? (
                <text
                  x="8"
                  y="50"
                  fontSize="10"
                  fontWeight="700"
                  fontFamily="ui-monospace, monospace"
                  fill="#b91c1c"
                >
                  OFFLINE [FAILED]
                </text>
              ) : isConsumer ? (
                <text
                  x="8"
                  y="50"
                  fontSize="10"
                  fontFamily="ui-monospace, monospace"
                  fill={node.is_fully_served ? '#15803d' : '#b45309'}
                >
                  {node.supplied} / {node.demand} req
                </text>
              ) : (
                <text
                  x="8"
                  y="50"
                  fontSize="10"
                  fontFamily="ui-monospace, monospace"
                  fill="#475569"
                >
                  {node.type === 'generator' ? `Gen: ${node.capacity}` : `Tput: ${node.capacity}`}
                </text>
              )}

              {/* Operational Indicator Dot */}
              <circle
                cx={BLOCK_WIDTH - 12}
                cy="16"
                r="3.5"
                fill={isFailed ? '#b91c1c' : '#15803d'}
              />
            </g>
          );
        })}
      </svg>
    </div>
  );
}
