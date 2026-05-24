# AI Change Log

## 2026-05-24

- Scope: `03-projects/sgc-internal-portal`
- Actor: Codex
- Type: rollout / documentation
- Summary:
  - Cloudflare Pages migration status was recorded and updated.
  - Old GitHub Pages migration notice was added and refined for company email OTP login.
  - The notice now states that only `@sgc-gold.co.jp` email addresses can log in and includes a copy button for the domain.
- Touched files:
  - `03-projects/sgc-internal-portal/index.html`
  - `03-projects/sgc-internal-portal/docs/cloudflare-pages-access-migration-plan.md`
  - `03-projects/sgc-internal-portal/docs/ai_change_log.md`
- Decisions locked:
  - Keep GitHub Pages public for now as an old-page notice path.
  - Continue using `https://sgc-internal-portal.pages.dev/`; do not use a custom domain.
  - Keep Cloudflare Access OTP restricted to `sgc-gold.co.jp` company email addresses.
  - Do not change `sw.js`, GAS, GitHub Pages deployment, repository visibility, or Cloudflare Access settings in this pass.
- Follow-ups:
  - Verify the old GitHub Pages banner after GitHub Pages deployment updates.
  - Continue testing Cloudflare Pages on iPhone, PWA, iframe pages, and login persistence.
