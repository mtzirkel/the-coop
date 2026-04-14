<script>
  let { jobs = "[]", csrfToken = "" } = $props();

  let jobList = $derived(typeof jobs === "string" ? JSON.parse(jobs) : jobs);

  let selectedJob = $state("");
  let date = $state(new Date().toISOString().split("T")[0]);
  let timeStart = $state("08:00");
  let timeEnd = $state("12:00");
  let location = $state("");
  let notes = $state("");
  let submitting = $state(false);
  let success = $state(false);
  let error = $state("");

  let calculatedHours = $derived(() => {
    if (!timeStart || !timeEnd) return 0;
    const [sh, sm] = timeStart.split(":").map(Number);
    const [eh, em] = timeEnd.split(":").map(Number);
    let diff = (eh * 60 + em) - (sh * 60 + sm);
    if (diff <= 0) diff += 24 * 60; // overnight
    return Math.round(diff / 60 * 100) / 100;
  });

  async function submit() {
    if (!selectedJob || !timeStart || !timeEnd) return;
    submitting = true;
    error = "";
    success = false;

    try {
      const res = await fetch("/api/hours/", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": csrfToken,
        },
        body: JSON.stringify({
          job_id: selectedJob,
          date,
          time_start: timeStart,
          time_end: timeEnd,
          location,
          notes,
        }),
      });

      if (!res.ok) {
        const data = await res.json();
        throw new Error(data.detail || "Failed to log hours");
      }

      success = true;
      selectedJob = "";
      timeStart = "08:00";
      timeEnd = "12:00";
      location = "";
      notes = "";
      setTimeout(() => (success = false), 3000);
    } catch (e) {
      error = e.message;
    } finally {
      submitting = false;
    }
  }
</script>

<form onsubmit={(e) => { e.preventDefault(); submit(); }} class="space-y-4">
  {#if success}
    <div class="flash flash--positive">Hours logged successfully!</div>
  {/if}

  {#if error}
    <div class="flash flash--negative">{error}</div>
  {/if}

  <div class="field">
    <label for="job" class="field__label">Job</label>
    <select id="job" bind:value={selectedJob} class="input input--select">
      <option value="">Select a job...</option>
      {#each jobList as job}
        <option value={job.id}>{job.name}</option>
      {/each}
    </select>
  </div>

  <div class="field">
    <label for="date" class="field__label">Date</label>
    <input id="date" type="date" bind:value={date} class="input" />
  </div>

  <div class="field-row">
    <div class="field">
      <label for="time-start" class="field__label">Started</label>
      <input id="time-start" type="time" bind:value={timeStart} class="input" />
    </div>
    <div class="field">
      <label for="time-end" class="field__label">Ended</label>
      <input id="time-end" type="time" bind:value={timeEnd} class="input" />
    </div>
    <div class="field field--computed">
      <span class="field__label">Hours</span>
      <span class="computed-hours">{calculatedHours()}</span>
    </div>
  </div>

  <div class="field">
    <label for="location" class="field__label">Location</label>
    <input
      id="location"
      type="text"
      bind:value={location}
      placeholder="North ridge, creek lot..."
      class="input"
    />
  </div>

  <div class="field">
    <label for="notes" class="field__label">Notes</label>
    <textarea
      id="notes"
      bind:value={notes}
      rows="2"
      placeholder="What did you work on?"
      class="input"
    ></textarea>
  </div>

  <button
    type="submit"
    disabled={submitting || !selectedJob || !timeStart || !timeEnd}
    class="btn btn--primary full-width"
  >
    {#if submitting}
      Logging...
    {:else}
      Log Hours
    {/if}
  </button>
</form>
