import React, { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { TrendingUp, TrendingDown, Target, AlertTriangle, GripVertical, ChevronDown } from 'lucide-react'

function MetricCard({ icon, label, value, isPositive, bgColor }) {
  const valueColor =
    isPositive === undefined
      ? 'text-gray-900'
      : isPositive
        ? 'text-green-600'
        : 'text-red-600'

  return (
    <div className={`rounded-lg p-3.5 ${bgColor}`}>
      <div className="mb-1.5 flex items-center gap-2">
        {icon}
        <span className="text-sm text-gray-500">{label}</span>
      </div>
      <div className={`text-base font-semibold ${valueColor}`}>{value}</div>
    </div>
  )
}

function StatusBadge({
  status,
  statusColor,
  editable = false,
  options = [],
  onStatusChange,
}) {
  const [open, setOpen] = useState(false)
  const ref = useRef(null)

  const derivedStatusColor = (() => {
    const s = String(status || '')
    if (s.includes('运行')) return 'bg-green-500 text-white'
    if (s.includes('测试')) return 'bg-blue-500 text-white'
    if (s.includes('已平仓')) return 'bg-gray-400 text-white'
    return statusColor || 'bg-gray-100 text-gray-700'
  })()

  useEffect(() => {
    if (!open) return undefined
    const onDoc = (e) => {
      if (ref.current && !ref.current.contains(e.target)) setOpen(false)
    }
    document.addEventListener('mousedown', onDoc)
    return () => document.removeEventListener('mousedown', onDoc)
  }, [open])

  if (!editable) {
    return (
      <span className={`rounded-full px-3 py-1.5 text-sm font-medium ${derivedStatusColor}`}>
        {status}
      </span>
    )
  }

  return (
    <div className="relative" ref={ref}>
      <button
        type="button"
        title="点击修改运行状态"
        className={`inline-flex items-center gap-1 rounded-full px-3 py-1.5 text-sm font-medium transition-opacity hover:opacity-90 ${derivedStatusColor}`}
        onClick={(e) => {
          e.preventDefault()
          e.stopPropagation()
          setOpen((v) => !v)
        }}
        onMouseDown={(e) => {
          e.preventDefault()
          e.stopPropagation()
        }}
      >
        {status}
        <ChevronDown className="h-3.5 w-3.5 opacity-90" />
      </button>
      {open && (
        <div
          className="absolute right-0 z-20 mt-1 min-w-[7.5rem] overflow-hidden rounded-lg border border-[#e5e7eb] bg-white py-1 shadow-lg"
          onClick={(e) => {
            e.preventDefault()
            e.stopPropagation()
          }}
          onMouseDown={(e) => e.stopPropagation()}
        >
          {options.map((opt) => (
            <button
              key={opt}
              type="button"
              className={`block w-full px-3 py-2 text-left text-sm transition-colors hover:bg-[#f3f4f6] ${
                opt === status ? 'font-semibold text-[#2563eb]' : 'text-[#374151]'
              }`}
              onClick={(e) => {
                e.preventDefault()
                e.stopPropagation()
                onStatusChange?.(opt)
                setOpen(false)
              }}
            >
              {opt}
            </button>
          ))}
        </div>
      )}
    </div>
  )
}

export function StrategyCardMatrix({
  to,
  title,
  code,
  description,
  status,
  statusColor,
  statusEditable = false,
  statusOptions = ['运行中', '已平仓', '测试中'],
  onStatusChange,
  progress,
  progressColor,
  annualReturn,
  annualReturnLabel = '当年收益',
  drawdown,
  profitFactor,
  riskIndex,
  isRiskWarning = false,
  isActive,
  icon,
  draggable = false,
  isDragging = false,
  isDragOver = false,
  onDragStart,
  onDragOver,
  onDragLeave,
  onDrop,
  onDragEnd,
  onNavigateClick,
}) {
  const content = (
    <>
      <div className="mb-4 flex items-start justify-between">
        <div className="flex items-center gap-3 flex-1 min-w-0">
          {draggable && (
            <span
              className="mt-1 shrink-0 cursor-grab text-[#9ca3af] active:cursor-grabbing"
              title="拖拽调整顺序"
              aria-hidden
            >
              <GripVertical className="h-5 w-5" />
            </span>
          )}
          {icon && (
            <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-gradient-to-br from-blue-50 to-indigo-100 text-2xl shadow-sm">
              {icon}
            </div>
          )}
          <div className="min-w-0">
            <h3 className="mb-1 text-xl font-bold text-gray-900">{title}</h3>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <StatusBadge
            status={status}
            statusColor={statusColor}
            editable={statusEditable}
            options={statusOptions}
            onStatusChange={onStatusChange}
          />
        </div>
      </div>
      <p className="strategy-card-desc mb-4 line-clamp-2 text-base leading-relaxed text-[#6b7280]">{description}</p>
      <div className="grid grid-cols-2 gap-3">
        <MetricCard
          icon={<TrendingUp className="h-5 w-5 text-blue-500" />}
          label={annualReturnLabel}
          value={annualReturn}
          isPositive={true}
          bgColor="bg-blue-50"
        />
        <MetricCard
          icon={<TrendingDown className="h-5 w-5 text-red-500" />}
          label="最大回撤"
          value={drawdown}
          isPositive={false}
          bgColor="bg-red-50"
        />
        <MetricCard
          icon={<Target className="h-5 w-5 text-green-600" />}
          label="盈亏比"
          value={profitFactor}
          bgColor="bg-green-50"
        />
        <MetricCard
          icon={
            <AlertTriangle
              className={`h-5 w-5 ${isRiskWarning ? 'text-red-500' : 'text-green-600'}`}
            />
          }
          label="风险指数"
          value={riskIndex}
          bgColor={isRiskWarning ? 'bg-red-50' : 'bg-green-50'}
        />
      </div>
    </>
  )

  const className = `strategy-card-matrix block rounded-xl border bg-white p-6 text-inherit no-underline transition-all duration-200 ${
    isDragging ? 'opacity-50 scale-[0.99]' : ''
  } ${
    isDragOver ? 'border-[#3b82f6] border-dashed shadow-[0_0_0_3px_rgba(59,130,246,0.15)]' : ''
  } ${
    isActive && !isDragOver
      ? 'border-[#3b82f6] shadow-[0_10px_25px_rgba(59,130,246,0.15)]'
      : !isDragOver
        ? 'border-[#e5e7eb] hover:border-[#3b82f6] hover:shadow-[0_10px_25px_rgba(59,130,246,0.15)] hover:-translate-y-0.5'
        : ''
  } ${draggable ? 'cursor-grab active:cursor-grabbing' : ''}`

  const dragProps = draggable
    ? {
        draggable: true,
        onDragStart,
        onDragOver,
        onDragLeave,
        onDrop,
        onDragEnd,
      }
    : {}

  if (to) {
    return (
      <Link to={to} className={className} onClick={onNavigateClick} {...dragProps}>
        {content}
      </Link>
    )
  }
  return (
    <div className={className} {...dragProps}>
      {content}
    </div>
  )
}
