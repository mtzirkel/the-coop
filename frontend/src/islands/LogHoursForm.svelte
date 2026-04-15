<script>
  let {
    jobs = "[]",
    csrfToken = "",
    isAdmin = false,
    otherMembers = "[]"
  } = $props();

  // jobs starts from the server-rendered list; we keep our own local copy so
  // when a new job is created inline we can prepend it without a page reload
  let jobList = $state(typeof jobs === "string" ? JSON.parse(jobs) : jobs);

  // Members the current admin can log hours on behalf of
  let memberList = $derived(
    typeof otherMembers === "string" ? JSON.parse(otherMembers) : otherMembers
  );

  // Sentinel value for the "Add new job..." dropdown option
  const NEW_JOB = "__new__";

  // "" = self, otherwise the target member's UUID
  let logForMemberId = $state("");
  let selectedJob = $state("");
  let newJobName = $state("");
  let date = $state(new Date().toISOString().split("T")[0]);
  let timeStart = $state("08:00");
  let timeEnd = $state("12:00");
  let location = $state("");
  let notes = $state("");
  let submitting = $state(false);
  let success = $state(false);
  let error = $state("");

  let isCreatingJob = $derived(selectedJob === NEW_JOB);

  let calculatedHours = $derived(() => {
    if (!timeStart || !timeEnd) return 0;
    const [sh, sm] = timeStart.split(":").map(Number);
    const [eh, em] = timeEnd.split(":").map(Number);
    let diff = (eh * 60 + em) - (sh * 60 + sm);
    if (diff <= 0) diff += 24 * 60; // overnight
    return Math.round(diff / 60 * 100) / 100;
  });

  let canSubmit = $derived(() => {
    if (!timeStart || !timeEnd) return false;
    if (isCreatingJob) return newJobName.trim().length > 0;
    return selectedJob !== "";
  });

  async function createJob(name) {
    const res = await fetch("/api/jobs/", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": csrfToken,
      },
      body: JSON.stringify({ name }),
    });
    if (!res.ok) {
      const data = await res.json().catch(() => ({}));
      throw new Error(data.detail || "Failed to create job");
    }
    return res.json();
  }

  async function submit() {
    if (!canSubmit()) return;
    submitting = true;
    error = "";
    success = false;

    try {
      // If user chose "+ Add new job..." create the job first, then log hours
      let jobId = selectedJob;
      if (isCreatingJob) {
        const newJob = await createJob(newJobName.trim());
        jobList = [...jobList, newJob].sort((a, b) => a.name.localeCompare(b.name));
        jobId = newJob.id;
      }

      const body = {
        job_id: jobId,
        date,
        time_start: timeStart,
        time_end: timeEnd,
        location,
        notes,
      };
      if (isAdmin && logForMemberId) {
        body.member_id = logForMemberId;
      }

      const res = await fetch("/api/hours/", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": csrfToken,
        },
        body: JSON.stringify(body),
      });

      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.detail || "Failed to log hours");
      }

      success = true;
      selectedJob = "";
      newJobName = "";
      logForMemberId = "";
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

  {#if isAdmin && memberList.length > 0}
    <div class="field">
      <label for="log-for" class="field__label">Logging for</label>
      <select id="log-for" bind:value={logForMemberId} class="input input--select">
        <option value="">Myself</option>
        {#each memberList as m}
          <option value={m.id}>{m.display_name}</option>
        {/each}
      </select>
    </div>
  {/if}

  <div class="field">
    <label for="job" class="field__label">Job</label>
    <select id="job" bind:value={selectedJob} class="input input--select">
      <option value="">Select a job...</option>
      {#each jobList as job}
        <option value={job.id}>{job.name}</option>
      {/each}
      <option value={NEW_JOB}>+ Add new job…</option>
    </select>
  </div>

  {#if isCreatingJob}
    <div class="field">
      <label for="new-job-name" class="field__label">New job name</label>
      <input
        id="new-job-name"
        type="text"
        bind:value={newJobName}
        placeholder="e.g. Equipment maintenance"
        class="input"
        autofocus
      />
    </div>
  {/if}

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
    disabled={submitting || !canSubmit()}
    class="btn btn--primary full-width"
  >
    {#if submitting}
      {isCreatingJob ? "Creating job..." : "Logging..."}
    {:else}
      Log Hours
    {/if}
  </button>
</form>
