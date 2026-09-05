import Link from 'next/link'

export default function WorkerNotFound() {
  return (
    <div className="page-heading">
      <div>
        <h1>
          Worker not found<span className="heading-period">.</span>
        </h1>
        <p>No worker with that id — it may never have reported a heartbeat.</p>
      </div>
      <Link href="/workers" className="outline-button" style={{ width: 'fit-content' }}>
        Back to workers
      </Link>
    </div>
  )
}
