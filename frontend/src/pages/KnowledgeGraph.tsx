import React, { useEffect } from 'react';
import { useVaultStore } from '../store/useVaultStore';
import {
  ReactFlow,
  Background,
  Controls,
  MiniMap,
  useNodesState,
  useEdgesState
} from '@xyflow/react';
import type { Node, Edge } from '@xyflow/react';

import '@xyflow/react/dist/style.css';
import { Network } from 'lucide-react';

export const KnowledgeGraph: React.FC = () => {
  const { graph, fetchGraph } = useVaultStore();

  const [nodes, setNodes, onNodesChange] = useNodesState<Node>([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState<Edge>([]);

  useEffect(() => {
    fetchGraph();
  }, []);

  // Compute node layouts dynamically using simple radial circle packing layout
  useEffect(() => {
    if (!graph || graph.nodes.length === 0) return;

    const documentNodes = graph.nodes.filter(n => n.type === 'document');
    const entityNodes = graph.nodes.filter(n => n.type === 'entity');

    // 1. Layout document nodes
    const docPositions: Record<string, { x: number; y: number }> = {};
    documentNodes.forEach((doc, idx) => {
      const x = 150 + idx * 360;
      const y = 100;
      docPositions[doc.id] = { x, y };
    });

    // 2. Find entity connections
    const entityConnections: Record<string, string[]> = {};
    entityNodes.forEach((ent) => {
      const connectedDocs = graph.edges
        .filter(edge => (edge.source === ent.id && documentNodes.some(d => d.id === edge.target)) ||
                        (edge.target === ent.id && documentNodes.some(d => d.id === edge.source)))
        .map(edge => edge.source === ent.id ? edge.target : edge.source);
      entityConnections[ent.id] = connectedDocs;
    });

    // 3. Track doc-specific single-connected entities
    const docEntities: Record<string, string[]> = {};
    documentNodes.forEach(d => { docEntities[d.id] = []; });
    const sharedEntities: string[] = [];
    const orphanEntities: string[] = [];

    entityNodes.forEach((ent) => {
      const docs = entityConnections[ent.id] || [];
      if (docs.length === 1) {
        docEntities[docs[0]].push(ent.id);
      } else if (docs.length > 1) {
        sharedEntities.push(ent.id);
      } else {
        orphanEntities.push(ent.id);
      }
    });

    // 4. Map final coordinates
    const mappedNodes = graph.nodes.map((node) => {
      let x = 0;
      let y = 0;

      if (node.type === 'document') {
        const pos = docPositions[node.id];
        x = pos.x;
        y = pos.y;
      } else {
        const docs = entityConnections[node.id] || [];
        if (docs.length === 1) {
          const docId = docs[0];
          const docPos = docPositions[docId];
          const entitiesList = docEntities[docId] || [];
          const entIdx = entitiesList.indexOf(node.id);
          const total = entitiesList.length;
          
          const startAngle = Math.PI / 6; // 30 degrees
          const endAngle = 5 * Math.PI / 6; // 150 degrees
          const angle = total > 1 
            ? startAngle + (entIdx / (total - 1)) * (endAngle - startAngle) 
            : Math.PI / 2; // Straight down
          
          x = docPos.x + 180 * Math.cos(angle);
          y = docPos.y + 180 * Math.sin(angle);
        } else if (docs.length > 1) {
          const xSum = docs.reduce((acc, dId) => acc + docPositions[dId].x, 0);
          const sharedIdx = sharedEntities.indexOf(node.id);
          x = xSum / docs.length;
          y = 320 + (sharedIdx * 60);
        } else {
          const orphanIdx = orphanEntities.indexOf(node.id);
          x = 150 + orphanIdx * 180;
          y = 480;
        }
      }

      // Enterprise Styling categories matching professional colors
      let bgClass = 'border-[#E5E7EB] dark:border-slate-800 bg-white dark:bg-slate-900';
      let textClass = 'text-[#111827] dark:text-slate-100';
      
      if (node.category === 'Identity') {
        bgClass = 'border-[#BFDBFE] dark:border-blue-900 bg-[#EFF6FF]/60 dark:bg-blue-950/20';
        textClass = 'text-[#1E40AF] dark:text-blue-400';
      } else if (node.category === 'Academic') {
        bgClass = 'border-[#C7D2FE] dark:border-indigo-900 bg-[#EEF2FF]/60 dark:bg-indigo-950/20';
        textClass = 'text-[#3730A3] dark:text-indigo-400';
      } else if (node.category === 'Professional') {
        bgClass = 'border-[#E9D5FF] dark:border-purple-900 bg-[#F5F3FF]/60 dark:bg-purple-950/20';
        textClass = 'text-[#6B21A8] dark:text-purple-400';
      } else if (node.category === 'Financial') {
        bgClass = 'border-[#A7F3D0] dark:border-emerald-900 bg-[#ECFDF5]/60 dark:bg-emerald-950/20';
        textClass = 'text-[#065F46] dark:text-emerald-400';
      } else if (node.type === 'entity') {
        bgClass = 'border-[#E5E7EB] dark:border-slate-800 bg-[#F9FAFB] dark:bg-slate-950';
        textClass = 'text-[#6B7280] dark:text-slate-400';
      }

      return {
        id: node.id,
        position: { x, y },
        data: {
          label: (
            <div className={`p-2 text-center select-none`}>
              <p className={`font-semibold text-xs truncate max-w-[110px] ${textClass}`}>{node.label}</p>
              <span className="text-[8px] uppercase tracking-wider opacity-60 block mt-0.5 font-bold">
                {node.type}
              </span>
            </div>
          )
        },
        style: {
          width: 130,
          borderRadius: '4px',
          borderWidth: '1px',
          boxShadow: '0 1px 2px rgba(0,0,0,0.015)'
        },
        className: bgClass
      };
    });

    const mappedEdges = graph.edges.map((edge) => ({
      id: edge.id,
      source: edge.source,
      target: edge.target,
      label: edge.label,
      animated: edge.label === 'PRECEDES' || edge.label === 'FOLLOWS',
      labelStyle: { fontSize: 8, fill: '#94A3B8', fontWeight: 600 },
      style: { stroke: '#E5E7EB' }
    }));

    setNodes(mappedNodes);
    setEdges(mappedEdges);
  }, [graph]);

  return (
    <div className="flex flex-col h-full overflow-hidden bg-[#F8FAFC] dark:bg-slate-950">
      
      {/* Top Header Bar */}
      <header className="h-14 border-b border-[#E5E7EB] dark:border-slate-800 bg-white dark:bg-slate-900 px-8 flex items-center justify-between shrink-0">
        <div className="flex items-center gap-2 text-xs text-[#6B7280]">
          <span>Analytics</span>
          <span>/</span>
          <span className="text-[#111827] dark:text-slate-200 font-medium">Knowledge Graph</span>
        </div>

        {/* Legend */}
        <div className="flex items-center gap-4 text-[10px] text-[#6B7280] font-semibold">
          <div className="flex items-center gap-1.5">
            <span className="w-2 h-2 rounded bg-[#EFF6FF] border border-[#BFDBFE]" />
            <span>Identity</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="w-2 h-2 rounded bg-[#EEF2FF] border border-[#C7D2FE]" />
            <span>Academic</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="w-2 h-2 rounded bg-[#F5F3FF] border border-[#E9D5FF]" />
            <span>Professional</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="w-2 h-2 rounded bg-[#ECFDF5] border border-[#A7F3D0]" />
            <span>Financial</span>
          </div>
        </div>
      </header>

      {/* Canvas */}
      <div className="flex-1 relative">
        {nodes.length > 0 ? (
          <ReactFlow
            nodes={nodes}
            edges={edges}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            fitView
            minZoom={0.2}
            maxZoom={1.2}
          >
            <Background color="#E2E8F0" gap={16} size={1} />
            <Controls className="!bg-white dark:!bg-slate-900 !border-[#E5E7EB] dark:!border-slate-800" />
            <MiniMap 
              nodeColor={() => '#E5E7EB'} 
              maskColor="rgba(248, 250, 252, 0.4)" 
              style={{ backgroundColor: 'var(--card)' }}
            />
          </ReactFlow>
        ) : (
          <div className="absolute inset-0 flex flex-col items-center justify-center text-[#6B7280] gap-2">
            <Network className="w-8 h-8 text-[#6B7280]/20" />
            <p className="text-xs">No semantic memories linked in the graph yet.</p>
          </div>
        )}
      </div>
    </div>
  );
};
