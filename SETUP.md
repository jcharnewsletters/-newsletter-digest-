# One-Time Setup Checklist (~45 minutes)

Follow these steps once and the digest runs itself forever after. Plain-English
definitions are included wherever a technical term is unavoidable.

---

## Step 1 — Create the dedicated Gmail inbox (~10 min)

This inbox exists only to receive newsletters; the agent reads it automatically.

1. Go to https://accounts.google.com/signup and create a new account, e.g.
   `jchar.newsletters@gmail.com`.
2. Turn on **2-Step Verification** (Google requires this before it will issue
   an app password): Google Account → Security → 2-Step Verification → follow
   the prompts with your phone.
3. Create an **app password** (a special 16-character password Google issues
   for one single app, so the agent never needs your real password and can be
   revoked anytime): Google Account → Security → search "App passwords" →
   name it `newsletter-digest` → copy the 16 characters somewhere safe.

## Step 2 — Subscribe the new address to every newsletter (~15 min)

Open each link **while signed into the new Gmail** and enter the new address:

This is the current tracked set (matches `config/newsletters.yml`). If you add
or drop a newsletter later, tell Claude Code the sender address and it updates
the config.

**AI** (morning 10 AM: Rundown, Neuron, Superhuman, TLDR AI, TAAFT, ultrathink;
evening 10 PM: Everyday AI, Lenny's, The Batch, AI Daily Brief, Dharmesh/simple.ai)
- The Rundown AI, The Neuron, Superhuman, TLDR AI, There's An AI For That,
  ultrathink, Everyday AI, Lenny's Newsletter, The Batch, AI Daily Brief,
  Dharmesh @ simple.ai

**Tech** (morning 10 AM)
- The Code, Techpresso, The Rundown Tech, TLDR (main)

**Crypto** (morning 9:30 AM: CMC Spotlight, CMC Market Pulse, CoinDesk Daybook,
CoinDesk Headlines, TLDR Crypto; evening 7 PM: Decrypt Daily Hash, Bitcoin Magazine)

**Stocks** (morning 9:15 AM)
- Opening Bell (Phil Rosen), Yahoo Finance Morning Brief, Wall Street Breakfast,
  Bloomberg, Investopedia Pre-Market, CNBC Morning Squawk

Make sure you've clicked the confirmation link in each welcome email.

## Step 3 — Get an Anthropic API key (~5 min)

The summarization runs on Claude via the API ("pay per use" — at this volume
expect roughly **$2–5/month**).

1. Go to https://console.anthropic.com/ and sign up.
2. Add a payment method (Billing) and, optionally, a monthly spend limit
   (e.g. $10) so cost can never surprise you.
3. API Keys → Create Key → copy the key (starts with `sk-ant-`).

## Step 4 — GitHub repository (~10 min)

GitHub runs the schedule (free) and hosts the website (free).

1. Create an account at https://github.com/ if you don't have one.
2. Create a new repository named `newsletter-digest` (public — required for
   free GitHub Pages hosting; see the privacy note below).
3. Push this folder to it (or ask Claude Code to do it for you).
4. Add the four secrets: repo → **Settings → Secrets and variables → Actions →
   New repository secret**:
   | Secret name | Value |
   |---|---|
   | `GMAIL_ADDRESS` | jchar.newsletter@gmail.com |
   | `GMAIL_APP_PASSWORD` | the 16-character app password (no spaces) |
   | `ALERT_RECIPIENT` | jchar.newsletter@gmail.com |
   | `ANTHROPIC_API_KEY` | the `sk-ant-...` key |
5. Same page, **Variables** tab → New repository variable:
   | Variable | Value |
   |---|---|
   | `SITE_URL` | `https://jcharnewsletters.github.io/-newsletter-digest-/` |
6. Enable the website: repo → **Settings → Pages** → Source: "Deploy from a
   branch" → Branch: `main`, folder: `/docs` → Save.

> **Privacy note:** a free GitHub Pages site is public at an obscure URL.
> Anyone who has the link could read your summaries (including summaries of
> paywalled newsletters). If that bothers you, skip Pages and rely on the
> email digests alone — everything else still works.

## Step 5 — Verify (~5 min, after the first newsletters arrive)

1. Wait a day so a few newsletters land in the inbox.
2. Check sender matching:
   ```
   pip install -r requirements.txt
   set GMAIL_ADDRESS=...           # PowerShell: $env:GMAIL_ADDRESS="..."
   set GMAIL_APP_PASSWORD=...
   python -m src.list_senders
   ```
   It prints a match count and sample subject for each newsletter. Any line
   showing **0 MATCHES** means the sender/subject pattern needs fixing — tell
   Claude Code what you see and it will correct `config/newsletters.yml`.
   (The subject-based ones — the three TLDR variants and the two CoinDesk
   feeds — are the most likely to need a tweak.)
3. Test one live batch from GitHub: repo → **Actions → Newsletter digest →
   Run workflow** → batch `ai-am`. Confirm:
   - the workflow goes green,
   - the site updated at your `SITE_URL`,
   - the alert email arrived at jchar.newsletter@gmail.com.

Done. The six daily schedules take over from here:

| Alert | Deadline (ET) | Covers |
|---|---|---|
| Morning Stocks | 9:15 AM | Opening Bell, Yahoo Finance, Wall Street Breakfast, Bloomberg, Investopedia Pre-Market, CNBC Morning Squawk |
| Morning Crypto | 9:30 AM | CMC Spotlight, CMC Market Pulse, CoinDesk Daybook, CoinDesk Headlines, TLDR Crypto |
| Morning AI | 10:00 AM | The Neuron, The Rundown AI, Superhuman, TLDR AI, TAAFT, ultrathink |
| Morning Tech | 10:00 AM | The Code, Techpresso, The Rundown Tech, TLDR (main) |
| Evening Crypto | 7:00 PM | Decrypt Daily Hash, Bitcoin Magazine |
| Evening AI | 10:00 PM | Everyday AI, Lenny's, The Batch, AI Daily Brief, Dharmesh @ simple.ai |

Weekly newsletters (The Batch, Lenny's, CMC Market Pulse, Dharmesh @ simple.ai)
simply appear in their batch on the day they publish and are silently skipped
otherwise.

> **Morning Tech time:** I defaulted the new Tech digest to a 10:00 AM ET
> alert (alongside AI). If you'd prefer it earlier, later, or in the evening,
> just say so and I'll change the one schedule.
