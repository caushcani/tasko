'use client'

import { ActiveAlerts } from './active-alerts'
import { ChannelsSection } from './channels-section'
import { EventsSection } from './events-section'
import { RulesSection } from './rules-section'

export function AlertsPage() {
  return (
    <div className="flex flex-col gap-[18px]">
      <div className="page-heading">
        <div>
          <div className="eyebrow">
            <span className="live-indicator" />
            Live monitoring
          </div>
          <h1>
            Alerts<span className="heading-period">.</span>
          </h1>
          <p>Rules the evaluator checks against your fleet, and where they notify.</p>
        </div>
      </div>

      <ActiveAlerts />
      <RulesSection />
      <ChannelsSection />
      <EventsSection />
    </div>
  )
}
