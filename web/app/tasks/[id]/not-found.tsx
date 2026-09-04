import Link from 'next/link'

export default function TaskNotFound() {
  return (
    <div className="page-heading">
      <div>
        <h1>
          Task not found<span className="heading-period">.</span>
        </h1>
        <p>No task with that id — it may have been pruned, or the link is wrong.</p>
      </div>
      <Link href="/tasks" className="outline-button" style={{ width: 'fit-content' }}>
        Back to tasks
      </Link>
    </div>
  )
}
