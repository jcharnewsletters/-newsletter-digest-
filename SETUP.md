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

**AI**
- [ ] The Rundown AI — https://www.therundown.ai/
- [ ] The Neuron — https://www.theneurondaily.com/
- [ ] Superhuman — https://www.superhuman.ai/
- [ ] TLDR AI — https://tldr.tech/ai
- [ ] Ben's Bites — https://www.bensbites.com/
- [ ] Everyday AI — https://read.youreverydayai.com/
- [ ] Lenny's Newsletter — https://www.lennysnewsletter.com/
- [ ] The Batch — https://www.deeplearning.ai/the-batch/
- [ ] AI Daily Brief — https://aidailybrief.beehiiv.com/

**Crypto**
- [ ] TLDR Crypto — https://tldr.tech/crypto
- [ ] CoinDesk Daybook US — https://www.coindesk.com/newsletters/daybook-us
- [ ] CMC newsletters (Spotlight + Market Pulse) — https://coinmarketcap.com/newsletter/
- [ ] Decrypt Daily Hash — https://decrypt.co/newsletters/daily-hash
- [ ] Bitcoin Magazine — https://bitcoinmagazine.com/newsletter

**Stocks**
- [ ] Opening Bell Daily — https://www.openingbelldailynews.com/
- [ ] Yahoo Finance newsletters — https://finance.yahoo.com/newsletters/
- [ ] Wall Street Breakfast — https://seekingalpha.com/free-investing-newsletters
- [ ] Bloomberg Morning Briefing: Americas — https://www.bloomberg.com/account/newsletters/morning-americas
- [ ] CNBC 5 Things — https://www.cnbc.com/5-things-to-know/
- [ ] Investopedia — https://www.investopedia.com/news (newsletter signup in page footer)

Click the confirmation link in each welcome email.

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
   | `GMAIL_ADDRESS` | the dedicated Gmail address |
   | `GMAIL_APP_PASSWORD` | the 16-character app password (no spaces) |
   | `ALERT_RECIPIENT` | jchar2017@gmail.com |
   | `ANTHROPIC_API_KEY` | the `sk-ant-...` key |
5. Same page, **Variables** tab → New repository variable:
   | Variable | Value |
   |---|---|
   | `SITE_URL` | `https://<your-github-username>.github.io/newsletter-digest/` |
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
   If any newsletter shows under "NOT matched", tell Claude Code the sender
   address and it will fix `config/newsletters.yml`.
3. Test one live batch from GitHub: repo → **Actions → Newsletter digest →
   Run workflow** → batch `ai-am`. Confirm:
   - the workflow goes green,
   - the site updated at your `SITE_URL`,
   - the alert email arrived at jchar2017@gmail.com.

Done. The five daily schedules take over from here:

| Alert | Deadline (ET) | Covers |
|---|---|---|
| Morning Stocks | 9:15 AM | Opening Bell, Yahoo Finance, Wall Street Breakfast, Bloomberg, CNBC, Investopedia |
| Morning Crypto | 9:30 AM | CMC Spotlight, CMC Market Pulse, CoinDesk Daybook, TLDR Crypto |
| Morning AI | 10:00 AM | The Neuron, The Rundown, Superhuman, TLDR AI, Ben's Bites |
| Evening Crypto | 7:00 PM | Decrypt Daily Hash, Bitcoin Magazine |
| Evening AI | 10:00 PM | Everyday AI, Lenny's, The Batch, AI Daily Brief |

Weekly newsletters (The Batch, Lenny's, CMC Market Pulse) simply appear in
their batch on the day they publish and are silently skipped otherwise.
