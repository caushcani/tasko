'use client'

import { AxisBottom, AxisLeft } from '@visx/axis'
import { curveMonotoneX } from '@visx/curve'
import { localPoint } from '@visx/event'
import { LinearGradient } from '@visx/gradient'
import { GridRows } from '@visx/grid'
import { Group } from '@visx/group'
import { scaleLinear, scaleTime } from '@visx/scale'
import { AreaClosed, Bar, Line, LinePath } from '@visx/shape'
import { defaultStyles, TooltipWithBounds, useTooltip } from '@visx/tooltip'
import { useQuery } from '@tanstack/react-query'
import { useCallback, useEffect, useLayoutEffect, useMemo, useRef, useState } from 'react'
import { fetchThroughput } from './fetch-stats'
import type { ThroughputBucket, ThroughputWindow } from './types'

// useLayoutEffect on the client (measure before paint, no flash), useEffect on
// the server (no-op — avoids React's SSR warning).
const useIsoLayoutEffect = typeof window !== 'undefined' ? useLayoutEffect : useEffect

/** Width of an element, tracked live — a tiny local stand-in for ParentSize
 * that measures synchronously so the chart is on screen at first paint. */
function useElementWidth<T extends HTMLElement>() {
  const ref = useRef<T>(null)
  const [width, setWidth] = useState(0)
  useIsoLayoutEffect(() => {
    const el = ref.current
    if (!el) return
    const measure = () => setWidth(el.clientWidth)
    measure()
    const ro = new ResizeObserver(measure)
    ro.observe(el)
    return () => ro.disconnect()
  }, [])
  return [ref, width] as const
}

const REFRESH_MS = 10_000
const RANGES: { label: string; window: ThroughputWindow }[] = [
  { label: '1 hour', window: '1h' },
  { label: '24 hours', window: '24h' },
  { label: '7 days', window: '7d' },
]

const CYAN = '#55d6c2'
const AMBER = '#e1a456'
const HEIGHT = 208
const MARGIN = { top: 10, right: 14, bottom: 22, left: 30 }

const getDate = (b: ThroughputBucket) => new Date(b.start)

export function ThroughputChart({ live }: { live: boolean }) {
  const [window, setWindow] = useState<ThroughputWindow>('24h')
  const { data } = useQuery({
    queryKey: ['stats', 'throughput', window],
    queryFn: () => fetchThroughput(window),
    refetchInterval: live ? REFRESH_MS : false,
    placeholderData: (prev) => prev,
  })

  const [plotRef, plotWidth] = useElementWidth<HTMLDivElement>()
  const buckets = data?.buckets ?? []
  const showFailed = (data?.total_failed ?? 0) > 0
  const bucketSeconds = data?.bucket_seconds ?? 3600

  return (
    <section className="panel throughput-panel">
      <div className="panel-heading">
        <div>
          <h2>Task throughput</h2>
          <p>Completed vs failed over time</p>
        </div>
        <div className="range-tabs">
          {RANGES.map((r) => (
            <button
              key={r.window}
              className={window === r.window ? 'selected' : ''}
              onClick={() => setWindow(r.window)}
            >
              {r.label}
            </button>
          ))}
        </div>
      </div>

      <div className="throughput-plot" ref={plotRef}>
        {buckets.length < 2 || plotWidth < 40 ? (
          <div className="chart-empty">
            {buckets.length < 2 ? 'Waiting for task data…' : ''}
          </div>
        ) : (
          <Plot
            width={plotWidth}
            buckets={buckets}
            window={window}
            showFailed={showFailed}
            bucketSeconds={bucketSeconds}
          />
        )}
      </div>

      <div className="chart-legend">
        <span>
          <i className="legend-dot cyan" />
          Completed <strong>{(data?.total_completed ?? 0).toLocaleString()}</strong>
        </span>
        <span>
          <i className="legend-dot amber" />
          Failed <strong>{(data?.total_failed ?? 0).toLocaleString()}</strong>
        </span>
      </div>
    </section>
  )
}

interface PlotProps {
  width: number
  buckets: ThroughputBucket[]
  window: ThroughputWindow
  showFailed: boolean
  bucketSeconds: number
}

function Plot({ width, buckets, window, showFailed, bucketSeconds }: PlotProps) {
  const innerW = Math.max(0, width - MARGIN.left - MARGIN.right)
  const innerH = HEIGHT - MARGIN.top - MARGIN.bottom

  const {
    showTooltip,
    hideTooltip,
    tooltipData,
    tooltipLeft = 0,
    tooltipTop = 0,
    tooltipOpen,
  } = useTooltip<ThroughputBucket>()

  const xScale = useMemo(
    () =>
      scaleTime({
        domain: [getDate(buckets[0]), getDate(buckets[buckets.length - 1])],
        range: [0, innerW],
      }),
    [buckets, innerW],
  )

  const maxY = useMemo(
    () => Math.max(1, ...buckets.map((b) => Math.max(b.completed, showFailed ? b.failed : 0))),
    [buckets, showFailed],
  )
  const yScale = useMemo(
    () => scaleLinear({ domain: [0, maxY], range: [innerH, 0], nice: true }),
    [maxY, innerH],
  )

  const handleMove = useCallback(
    (event: React.MouseEvent<SVGRectElement> | React.TouchEvent<SVGRectElement>) => {
      const point = localPoint(event)
      if (!point) return
      const x = point.x - MARGIN.left
      const frac = innerW > 0 ? x / innerW : 0
      const idx = Math.min(buckets.length - 1, Math.max(0, Math.round(frac * (buckets.length - 1))))
      const d = buckets[idx]
      showTooltip({
        tooltipData: d,
        tooltipLeft: xScale(getDate(d)),
        tooltipTop: yScale(Math.max(d.completed, showFailed ? d.failed : 0)),
      })
    },
    [buckets, innerW, xScale, yScale, showFailed, showTooltip],
  )

  if (width < 10) return null

  return (
    <div style={{ position: 'relative' }}>
      <svg width={width} height={HEIGHT}>
        <LinearGradient id="tp-area" from={CYAN} to={CYAN} fromOpacity={0.26} toOpacity={0} />
        <Group left={MARGIN.left} top={MARGIN.top}>
          <GridRows
            scale={yScale}
            width={innerW}
            numTicks={4}
            stroke="#233139"
            strokeDasharray="3,3"
          />
          <AreaClosed
            data={buckets}
            x={(d) => xScale(getDate(d)) ?? 0}
            y={(d) => yScale(d.completed) ?? 0}
            yScale={yScale}
            curve={curveMonotoneX}
            fill="url(#tp-area)"
          />
          <LinePath
            data={buckets}
            x={(d) => xScale(getDate(d)) ?? 0}
            y={(d) => yScale(d.completed) ?? 0}
            curve={curveMonotoneX}
            stroke={CYAN}
            strokeWidth={2}
          />
          {showFailed && (
            <LinePath
              data={buckets}
              x={(d) => xScale(getDate(d)) ?? 0}
              y={(d) => yScale(d.failed) ?? 0}
              curve={curveMonotoneX}
              stroke={AMBER}
              strokeWidth={1.5}
            />
          )}
          <AxisLeft
            scale={yScale}
            numTicks={4}
            hideAxisLine
            hideTicks
            tickFormat={(v) => fmtCount(Number(v))}
            tickLabelProps={() => ({ fill: '#596a73', fontSize: 9, textAnchor: 'end', dx: -6, dy: 3 })}
          />
          <AxisBottom
            scale={xScale}
            top={innerH}
            numTicks={Math.min(6, buckets.length)}
            hideAxisLine
            hideTicks
            tickFormat={(v) => formatTick(v as Date, window)}
            tickLabelProps={() => ({ fill: '#596a73', fontSize: 9, textAnchor: 'middle', dy: 4 })}
          />
          {tooltipOpen && tooltipData && (
            <g>
              <Line
                from={{ x: tooltipLeft, y: 0 }}
                to={{ x: tooltipLeft, y: innerH }}
                stroke="#3d4f57"
                strokeWidth={1}
                strokeDasharray="3,2"
                pointerEvents="none"
              />
              <circle
                cx={tooltipLeft}
                cy={yScale(tooltipData.completed)}
                r={3.5}
                fill={CYAN}
                stroke="#0d151a"
                strokeWidth={1.5}
                pointerEvents="none"
              />
              {showFailed && (
                <circle
                  cx={tooltipLeft}
                  cy={yScale(tooltipData.failed)}
                  r={3}
                  fill={AMBER}
                  stroke="#0d151a"
                  strokeWidth={1.5}
                  pointerEvents="none"
                />
              )}
            </g>
          )}
          <Bar
            x={0}
            y={0}
            width={innerW}
            height={innerH}
            fill="transparent"
            onMouseMove={handleMove}
            onMouseLeave={hideTooltip}
            onTouchStart={handleMove}
            onTouchMove={handleMove}
          />
        </Group>
      </svg>

      {tooltipOpen && tooltipData && (
        <TooltipWithBounds
          top={tooltipTop + MARGIN.top}
          left={tooltipLeft + MARGIN.left}
          style={{
            ...defaultStyles,
            background: '#16232a',
            border: '1px solid #2b3c43',
            borderRadius: 6,
            color: '#c0cccb',
            fontSize: 10,
            lineHeight: 1.7,
            padding: '7px 9px',
            pointerEvents: 'none',
          }}
        >
          <div style={{ color: '#8fa2ab', marginBottom: 2 }}>
            {formatRange(tooltipData, bucketSeconds, window)}
          </div>
          <div>
            <span style={{ color: CYAN }}>●</span> Completed{' '}
            <strong style={{ color: '#dde9e8' }}>{tooltipData.completed}</strong>
          </div>
          {showFailed && (
            <div>
              <span style={{ color: AMBER }}>●</span> Failed{' '}
              <strong style={{ color: '#dde9e8' }}>{tooltipData.failed}</strong>
            </div>
          )}
        </TooltipWithBounds>
      )}
    </div>
  )
}

function fmtCount(n: number): string {
  return n >= 1000 ? `${(n / 1000).toFixed(1)}k` : String(n)
}

function formatTick(d: Date, window: ThroughputWindow): string {
  return window === '7d'
    ? d.toLocaleDateString(undefined, { weekday: 'short' })
    : d.toLocaleTimeString(undefined, { hour: '2-digit', minute: '2-digit', hour12: false })
}

function formatRange(b: ThroughputBucket, bucketSeconds: number, window: ThroughputWindow): string {
  const start = new Date(b.start)
  const end = new Date(start.getTime() + bucketSeconds * 1000)
  const time = (d: Date) =>
    d.toLocaleTimeString(undefined, { hour: '2-digit', minute: '2-digit', hour12: false })
  if (window === '7d') {
    return `${start.toLocaleDateString(undefined, { weekday: 'short', month: 'short', day: 'numeric' })}, ${time(start)}`
  }
  return `${time(start)} – ${time(end)}`
}
