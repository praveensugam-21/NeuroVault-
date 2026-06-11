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

    const mappedNodes = graph.nodes.map((node) => {
      let x = 0;

      let y = 0;

      if (node.type === 'document') {
        // Position documents in an inner circle
        const angle = (documentNodes.indexOf(node) / Math.max(1, documentNodes.length)) * 2 * Math.PI;
        x = 250 + 220 * Math.cos(angle);
        y = 250 + 220 * Math.sin(angle);
      } else {
        // Position entity nodes in an outer circle
        const angle = (entityNodes.indexOf(node) / Math.max(1, entityNodes.length)) * 2 * Math.PI;
        x = 250 + 420 * Math.cos(angle);
        y = 250 + 420 * Math.sin(angle);
      }

      // Determine styling class based on category
      let bgClass = 'border-slate-300 dark:border-slate-700 bg-card';
      let textClass = 'text-foreground';
      
      if (node.category === 'Identity') {
        bgClass = 'border-blue-400 dark:border-blue-600 bg-blue-50/10 dark:bg-blue-950/20';
        textClass = 'text-blue-700 dark:text-blue-400';
      } else if (node.category === 'Academic') {
        bgClass = 'border-indigo-400 dark:border-indigo-600 bg-indigo-50/10 dark:bg-indigo-950/20';
        textClass = 'text-indigo-700 dark:text-indigo-400';
      } else if (node.category === 'Professional') {
        bgClass = 'border-purple-400 dark:border-purple-600 bg-purple-50/10 dark:bg-purple-950/20';
        textClass = 'text-purple-700 dark:text-purple-400';
      } else if (node.category === 'Financial') {
        bgClass = 'border-emerald-400 dark:border-emerald-600 bg-emerald-50/10 dark:bg-emerald-950/20';
        textClass = 'text-emerald-700 dark:text-emerald-400';
      } else if (node.type === 'entity') {
        bgClass = 'border-slate-200 dark:border-slate-800 bg-secondary/50';
        textClass = 'text-muted-foreground';
      }

      return {
        id: node.id,
        position: { x, y },
        data: {
          label: (
            <div className={`p-2 font-medium text-xs rounded transition-all text-center ${textClass}`}>
              <p className="font-bold truncate max-w-[120px]">{node.label}</p>
              <p className="text-[8px] uppercase opacity-75 tracking-wider mt-0.5">{node.type}</p>
            </div>
          )
        },
        style: {
          width: 140,
          borderRadius: '6px',
          borderWidth: '1.5px',
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
      labelStyle: { fontSize: 8, fill: 'var(--muted-foreground)', fontWeight: 600 },
      style: { stroke: 'var(--border)' }
    }));

    setNodes(mappedNodes);
    setEdges(mappedEdges);
  }, [graph]);

  return (
    <div className="flex flex-col h-full overflow-hidden">
      {/* Header */}
      <div className="p-8 border-b border-border shrink-0 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Semantic Knowledge Graph</h1>
          <p className="text-muted-foreground text-sm">
            Interactive visualization of extracted entities linked by semantic relationships.
          </p>
        </div>
        <div className="flex items-center gap-6 text-xs text-muted-foreground border border-border p-3 rounded bg-card">
          <div className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded-full bg-blue-500/20 border border-blue-500" />
            <span>Identity</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded-full bg-indigo-500/20 border border-indigo-500" />
            <span>Academic</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded-full bg-purple-500/20 border border-purple-500" />
            <span>Professional</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded-full bg-slate-300 dark:bg-slate-700 border border-slate-400" />
            <span>Entities</span>
          </div>
        </div>
      </div>

      {/* Canvas */}
      <div className="flex-1 relative bg-background/50">
        {nodes.length > 0 ? (
          <ReactFlow
            nodes={nodes}
            edges={edges}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            fitView
            minZoom={0.2}
            maxZoom={1.5}
          >
            <Background color="var(--border)" gap={16} size={1} />
            <Controls />
            <MiniMap 
              nodeColor={() => 'var(--border)'} 
              maskColor="rgba(var(--background), 0.3)" 
              style={{ backgroundColor: 'var(--card)' }}
            />
          </ReactFlow>
        ) : (
          <div className="absolute inset-0 flex flex-col items-center justify-center text-muted-foreground gap-3">
            <Network className="w-10 h-10 text-muted-foreground/30 animate-pulse" />
            <p className="text-xs">No graph entities linked yet. Please upload completed documents to populate.</p>
          </div>
        )}
      </div>
    </div>
  );
};
