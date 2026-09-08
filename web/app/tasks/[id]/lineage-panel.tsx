'use client'

import Dagre from '@dagrejs/dagre'
import {
  Background,
  Controls,
  Handle,
  Position,
  ReactFlow,
  type Edge,
  type Node,
  type NodeProps,
} from '@xyflow/react'
import '@xyflow/react/dist/style.css'
import { useRouter } from 'next/navigation'
import { useMemo } from 'react'
import type { TaskGraphOut, TaskState } from '../types'

const NODE_W = 190
const NODE_H = 58

const STATE_COLOR: Record<TaskState, string> = {
  success: '#58cdbb',
  failure: '#e4877f',
  started: '#73a9ea',
  queued: '#bd9ae7',
  retry: '#bd9ae7',
}

type TaskNodeData = {
  label: string
  queue: string
  state: TaskState
  isRoot: boolean
}

function TaskNode({ data }: NodeProps<Node<TaskNodeData>>) {
  const color = STATE_COLOR[data.state]
  return (
    <div
      style={{
        width: NODE_W,
        height: NODE_H,
        borderRadius: 8,
        border: `1px solid ${data.isRoot ? color : '#2b3c43'}`,
        boxShadow: data.isRoot ? `0 0 0 3px ${color}33` : 'none',
        background: '#131f25',
        padding: '8px 11px',
        display: 'flex',
        flexDirection: 'column',
        gap: 4,
        cursor: data.isRoot ? 'default' : 'pointer',
      }}
    >
      <Handle type="target" position={Position.Top} style={{ opacity: 0 }} />
      <div
        style={{
          fontFamily: 'var(--font-mono), monospace',
          fontSize: 11,
          color: '#d6e2e1',
          overflow: 'hidden',
          textOverflow: 'ellipsis',
          whiteSpace: 'nowrap',
        }}
      >
        {data.label}
      </div>
      <div style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 9 }}>
        <span style={{ width: 6, height: 6, borderRadius: 999, background: color }} />
        <span style={{ color, textTransform: 'capitalize' }}>{data.state}</span>
        <span style={{ color: '#6d7e86' }}>· {data.queue}</span>
      </div>
      <Handle type="source" position={Position.Bottom} style={{ opacity: 0 }} />
    </div>
  )
}

const nodeTypes = { taskNode: TaskNode }

function layout(graph: TaskGraphOut): { nodes: Node<TaskNodeData>[]; edges: Edge[] } {
  const g = new Dagre.graphlib.Graph().setDefaultEdgeLabel(() => ({}))
  g.setGraph({ rankdir: 'TB', nodesep: 28, ranksep: 46 })
  graph.nodes.forEach((n) => g.setNode(n.id, { width: NODE_W, height: NODE_H }))
  graph.edges.forEach((e) => g.setEdge(e.source, e.target))
  Dagre.layout(g)

  const nodes: Node<TaskNodeData>[] = graph.nodes.map((n) => {
    const pos = g.node(n.id)
    return {
      id: n.id,
      type: 'taskNode',
      position: { x: pos.x - NODE_W / 2, y: pos.y - NODE_H / 2 },
      data: {
        label: n.name,
        queue: n.queue,
        state: n.state,
        isRoot: n.id === graph.root_id,
      },
    }
  })

  const edges: Edge[] = graph.edges.map((e) => ({
    id: `${e.source}->${e.target}`,
    source: e.source,
    target: e.target,
    animated: false,
    style: { stroke: '#3a4c54', strokeWidth: 1.5 },
  }))

  return { nodes, edges }
}

export function LineagePanel({ graph }: { graph: TaskGraphOut }) {
  const router = useRouter()
  const { nodes, edges } = useMemo(() => layout(graph), [graph])

  // one node = the task itself, no lineage worth showing
  if (graph.nodes.length <= 1) return null

  return (
    <section className="panel" style={{ padding: 0, overflow: 'hidden' }}>
      <div className="panel-heading" style={{ padding: '18px 20px 14px' }}>
        <div>
          <h2>Lineage</h2>
          <p>What triggered what — {graph.nodes.length} tasks in this chain</p>
        </div>
      </div>
      <div style={{ height: 400, borderTop: '1px solid #223039' }}>
        <ReactFlow
          nodes={nodes}
          edges={edges}
          nodeTypes={nodeTypes}
          fitView
          fitViewOptions={{ padding: 0.2 }}
          nodesDraggable={false}
          nodesConnectable={false}
          edgesFocusable={false}
          proOptions={{ hideAttribution: true }} // permitted for open-source projects
          onNodeClick={(_, node) => {
            if (node.id !== graph.root_id) router.push(`/tasks/${node.id}`)
          }}
          colorMode="dark"
        >
          <Background color="#1c2930" gap={18} />
          <Controls showInteractive={false} />
        </ReactFlow>
      </div>
    </section>
  )
}
