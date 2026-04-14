<script>
  let { myHours = 0, teamHours = 0, projectedCut = 0 } = $props();

  let percentage = $derived(teamHours > 0 ? Math.round((myHours / teamHours) * 100) : 0);
</script>

<div class="grid-3">
  <div class="stat">
    <div class="stat__value">{myHours}</div>
    <div class="stat__label">My Hours</div>
  </div>

  <div class="stat">
    <div style="position: relative; width: 4rem; height: 4rem; margin: 0 auto;">
      <svg viewBox="0 0 36 36" style="width: 4rem; height: 4rem; transform: rotate(-90deg);">
        <path
          d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
          fill="none"
          stroke="var(--color-ring-track, oklch(88% 0.01 85))"
          stroke-width="3"
        />
        <path
          d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
          fill="none"
          stroke="var(--color-ring-fill, oklch(58% 0.16 80))"
          stroke-width="3"
          stroke-dasharray="{percentage}, 100"
          style="transition: stroke-dasharray 700ms ease-out;"
        />
      </svg>
      <div style="position: absolute; inset: 0; display: flex; align-items: center; justify-content: center;">
        <span style="font-size: 0.8125rem; font-weight: 800; color: var(--color-ink);">{percentage}%</span>
      </div>
    </div>
    <div class="stat__label" style="margin-top: 0.375rem">Of Team</div>
  </div>

  <div class="stat">
    <div class="stat__value text-positive">${projectedCut}</div>
    <div class="stat__label">Projected Cut</div>
  </div>
</div>
