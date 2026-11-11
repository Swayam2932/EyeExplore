# EyeExplore

Marketing site and shell for **EyeExplore**, a visual eyetracking dashboard for researchers, UX designers, and cognitive psychologists.

## Routes

| Path | Purpose |
|------|---------|
| `/` | Landing page |
| `/dashboard-app/` | Full-page Python/Dash analysis workspace |
| `/user-study/` | Participant login and four-task study portal (served by the root Python launcher) |
| `/docs` | Data schema, I-VT parameters, CSV troubleshooting |
| `/tutorials` | Onboarding, video placeholders, sample datasets |
| `/gallery` | Use-case gallery |
| `/support` | Issue form, FAQ, community contact |

## Integrated server launch

From the repository root, install Python requirements and run `npm ci` in this
directory once. Activate the `eye/` virtual environment, then start the landing
site, Python dashboard, and user-study portal together with `python main.py`.
The unified server defaults to port 8000; set `PORT` to the port required by
your host. It builds this Next.js app on startup and serves Dash under
`/dashboard-app/` plus the study portal under `/user-study/` on the same origin.
The landing navigation no longer has a Dashboard tab; each Launch Dashboard
button opens that full-page workspace in a new browser tab.

## Develop

```bash
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000).

For standalone frontend work, use `npm run dev`. The integrated launcher is
the deployment path that connects the dashboard iframe to the Dash process.
