"use client";

import { FormEvent, useState } from "react";

export function SupportForm() {
  const [sent, setSent] = useState(false);

  function onSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setSent(true);
  }

  if (sent) {
    return (
      <div className="rounded-2xl border border-mist bg-white p-8 text-center shadow-sm">
        <p className="text-lg font-semibold text-navy-900">Report received</p>
        <p className="mt-2 text-sm text-muted">
          This demo form does not send email. Wire it to your issue tracker or
          support inbox when you deploy.
        </p>
        <button
          type="button"
          className="mt-4 text-sm font-semibold text-navy-900 underline decoration-heat-orange underline-offset-4"
          onClick={() => setSent(false)}
        >
          Submit another
        </button>
      </div>
    );
  }

  return (
    <form onSubmit={onSubmit} className="rounded-2xl border border-mist bg-white p-6 shadow-sm sm:p-8">
      <div className="grid gap-4 sm:grid-cols-2">
        <label className="text-sm font-medium text-navy-900">
          Name
          <input
            required
            name="name"
            className="mt-1.5 w-full rounded-xl border border-mist bg-ice px-3 py-2.5 text-sm outline-none ring-heat-orange/40 focus:ring-2"
            placeholder="Dr. Ada"
          />
        </label>
        <label className="text-sm font-medium text-navy-900">
          Email
          <input
            required
            type="email"
            name="email"
            className="mt-1.5 w-full rounded-xl border border-mist bg-ice px-3 py-2.5 text-sm outline-none ring-heat-orange/40 focus:ring-2"
            placeholder="you@lab.edu"
          />
        </label>
      </div>
      <label className="mt-4 block text-sm font-medium text-navy-900">
        Topic
        <select
          name="topic"
          className="mt-1.5 w-full rounded-xl border border-mist bg-ice px-3 py-2.5 text-sm outline-none ring-heat-orange/40 focus:ring-2"
        >
          <option>Bug report</option>
          <option>Parse / CSV error</option>
          <option>Feature request</option>
          <option>Collaboration</option>
        </select>
      </label>
      <label className="mt-4 block text-sm font-medium text-navy-900">
        Message
        <textarea
          required
          name="message"
          rows={5}
          className="mt-1.5 w-full rounded-xl border border-mist bg-ice px-3 py-2.5 text-sm outline-none ring-heat-orange/40 focus:ring-2"
          placeholder="Describe the stimulus, tracker, and what you expected to see…"
        />
      </label>
      <button
        type="submit"
        className="heat-gradient mt-5 rounded-full px-5 py-2.5 text-sm font-semibold text-white"
      >
        Submit issue
      </button>
    </form>
  );
}
