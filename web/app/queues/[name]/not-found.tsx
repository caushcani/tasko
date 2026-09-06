import Link from 'next/link'

export default function QueueNotFound() {
  return (
    <div className="page-heading">
      <div>
        <h1>
          Queue not found<span className="heading-period">.</span>
        </h1>
        <p>The broker isn't holding a queue by that name right now.</p>
      </div>
      <Link href="/queues" className="outline-button" style={{ width: 'fit-content' }}>
        Back to queues
      </Link>
    </div>
  )
}
