import Link from 'next/link'

export default function ScheduleNotFound() {
  return (
    <div className="page-heading">
      <div>
        <h1>
          Schedule not found<span className="heading-period">.</span>
        </h1>
        <p>No schedule with that id — it may have been removed from its source.</p>
      </div>
      <Link href="/schedules" className="outline-button" style={{ width: 'fit-content' }}>
        Back to schedules
      </Link>
    </div>
  )
}
