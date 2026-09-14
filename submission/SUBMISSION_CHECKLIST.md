# Submission checklist — deadline Sep 14, 2026, 5:00 pm PDT (8:00 pm Eastern)

Do these in order. Estimated time: 90 minutes if nothing breaks.

## 1. GitHub repo (15 min)
- [ ] Repo already created: https://github.com/jgios21-afk/Quiet-Office
- [ ] Unzip `quiet-office.zip`, then in that folder:
  ```
  git init && git add . && git commit -m "Quiet Office — Agents for Humans Hackathon"
  git branch -M main
  git remote add origin https://github.com/jgios21-afk/Quiet-Office.git
  git push -u origin main
  ```
- [ ] On the repo page, click the gear next to "About" → set description → check that License shows **Apache-2.0** (GitHub detects it from LICENSE)
- [ ] Open README on GitHub and confirm the architecture image renders

## 2. AWS Builder ID (5 min)
- [ ] https://profile.aws.amazon.com → create a Builder ID with your email. You'll enter it on the Devpost form.

## 3. Verify it runs (10 min)
- [ ] `pip install -e ".[dev]"` then `pytest -q` → 8 passed
- [ ] `export QUIET_OFFICE_PROVIDER=scripted && quiet-office seed && quiet-office daily && quiet-office inbox`
- [ ] If you have AWS credentials with Bedrock access: `export QUIET_OFFICE_PROVIDER=bedrock` and rerun `daily` for the video. If not, record with `scripted` and say so on screen.

## 4. Record the video (30 min)
- [ ] Follow `VIDEO_SCRIPT.md`. Max 5:00. Screen + voice; no camera needed.
- [ ] Upload to YouTube (unlisted is fine) or Vimeo. Copy the link.

## 5. Devpost form (15 min)
- [ ] Join the hackathon: https://agentsforhumans.devpost.com/ → Join hackathon
- [ ] "My projects" → Create project
- [ ] Title: **Quiet Office**  ·  Tagline: *The back office that only speaks up when it matters.*
- [ ] Paste `DEVPOST_DESCRIPTION.md` into the description (Devpost accepts Markdown)
- [ ] Repo URL, video URL, Builder ID, track = **Professional Agents**
- [ ] Upload `docs/architecture.png` as the architecture diagram / project image
- [ ] "Built with": Python, Strands Agents, Amazon Bedrock, Amazon Bedrock AgentCore
- [ ] Submit — then re-open the project page and check every link works while logged out

## 6. Bonus points (optional, 20 min, only if time remains)
- [ ] Post on https://builder.aws.com with **"Agents for Humans"** in the title. Use the "Inspiration / How we built it / What we learned" sections from the description. Must be public before the deadline.

## If something fails
- Tests fail on install → `pip install --upgrade strands-agents` (code targets 1.x)
- Bedrock error → switch to `scripted` for the recording; the submission is still valid
- Video over 5:00 → cut the interactive "ask" beat first
