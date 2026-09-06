import { fetchQueues } from './fetch-queues'
import { QueuesTable } from './queues-table'

// Fetched once per request, handed to a client component as props — no
// URL-synced pagination to keep in step (queues aren't paginated).
export default async function QueuesPage() {
  const queues = await fetchQueues()

  return (
    <>
      <div className="page-heading">
        <div>
          <div className="eyebrow">
            <span className="live-indicator" />
            Live monitoring
          </div>
          <h1>
            Queues<span className="heading-period">.</span>
          </h1>
          <p>Current depth of every queue the broker is holding.</p>
        </div>
      </div>

      <section className="panel tasks-panel" style={{ padding: '20px' }}>
        <QueuesTable queues={queues} />
      </section>
    </>
  )
}
