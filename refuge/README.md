# Refuge

The prayer companion app. These files are deliberately **outside** `site/`, which
is the only directory GitHub Pages publishes — so Refuge is no longer served on
the public website.

- `faith/` — the web app (PWA)
- `app/` — alternate build
- `../ios/` — the native iOS wrapper, which bundles its own copy of the web app
  from `ios/Refuge/Web/index.html` and does not load anything from the web.

To publish it again, move a folder back under `site/`.
