# rocky-balala - repo rules

**Retrofitted by `/init-client --retrofit` on 2026-08-21 from what was on disk.** Every line below
is either DETECTED or explicitly UNKNOWN. Nothing here was inferred and then stated as fact. Correct
it the first time you work in this repo.

## Stack
Single-file static HTML/CSS/JS. No framework.

## Deploy target
**Hostinger static** (`.htaccess` present on disk).

## Does a push publish?
**Probably NO.** Hostinger deploys go through the Hostinger MCP, not a git push
(see the vault note `deploy-via-hostinger-mcp`). `frontline-website` is the known
exception. UNCONFIRMED for this repo; verify before assuming either way.

## Remote
`git@github.com:tannermosher2015-debug/RockyBalalaAgent.git`, branch `main`.

## Verify path
`shot.ps1` desktop + mobile, **both reviewed**, plus `impeccable detect` on the
built HTML. Every edit gets both shots before a deploy, including one-character ones.

## Landmines
<Empty. Add each one the day it bites, with the date.>
