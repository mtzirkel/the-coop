# How to Sign In to The Coop

Welcome! Here's how to get into The Coop and start logging your hours.

## What You Need

- An **authenticator app** on your phone — any of these work:
  - Google Authenticator
  - Authy
  - 1Password
  - Bitwarden
  - Microsoft Authenticator
  - Apple Passwords (built into iOS 17+)
- About 5 minutes for the initial setup

## First Time Setup

### 1. Request Access

Go to **https://auth.noegosunderwater.com/request-access**

Fill out the short form:
- **Username** — pick something simple like your first name (`mike`, `sarah`)
- **Optional message** — let Travis know who you are if it isn't obvious

Click **Submit**. You'll see a "request received" message.

### 2. Wait for Travis to Approve

Travis will get notified, approve your account, and grant you access to The Coop. He'll send you a one-time setup link that looks like:

```
https://auth.noegosunderwater.com/setup/abc123...
```

> ⚠️ **This link only works once.** Open it on whatever device has your authenticator app handy.

### 3. Scan the QR Code

When you open the setup link you'll see a QR code on the screen.

1. Open your authenticator app
2. Tap the **+** to add an account
3. Choose **Scan QR code**
4. Point your camera at the screen

Your authenticator will save the entry as **NoEgos Auth: yourusername** and start showing a 6-digit code that changes every 30 seconds.

> 💾 **Save the manual key as a backup.** Below the QR code is a "Manual entry key" you can expand. Save that text to a password manager (1Password, Bitwarden) — if you ever lose your phone you'll need it to recover.

### 4. Verify Your Setup

Type the current 6-digit code from your authenticator into the box on the page and click **Verify**. You're now set up!

## Signing In (Every Time)

1. Go to **https://coop.noegosunderwater.com**
2. You'll be redirected to the login page at `auth.noegosunderwater.com`
3. Enter your **username** and the current **6-digit code** from your authenticator
4. Click **Sign In**
5. You'll be redirected back to The Coop dashboard

You stay signed in for **90 days**. After that you'll need to sign in again with a fresh code.

## Logging Hours

1. Click **+ Log Hours** from the dashboard or the Hours page
2. Pick the **Job** you worked on
   - If your job isn't in the list, scroll to the bottom and pick **+ Add new job…** — you can name it on the spot
3. Set the **Date** (defaults to today)
4. Set **Started** and **Ended** times — the hours calculate automatically
5. Optionally add a **Location** (e.g. "north ridge", "Peterson's lot") and **Notes**
6. Click **Log Hours**

That's it. Your entry shows up immediately on your Hours page.

### If You're a Kid

Your time entries will go into a **pending** state until your assigned approver (your parent or guardian) approves them. You can still see them in your Hours list — they'll just have a "Pending" badge until approved.

## Working Offline

The Coop is built to work in the woods. If you log hours without signal:
- A yellow bar appears at the top: **"You're offline — changes will sync when you reconnect"**
- Your entries get saved on your phone
- When you get back to WiFi or cell signal, everything syncs automatically

> 📲 **Tip:** Visit each page (Dashboard, Hours, Log Hours, Inventory) at least once while you have signal so the app caches them for offline use.

## Installing as an App

You can pin The Coop to your home screen so it opens like a native app:

**On iPhone (Safari):**
1. Visit https://coop.noegosunderwater.com
2. Tap the **Share** button
3. Scroll down and tap **Add to Home Screen**

**On Android (Chrome):**
1. Visit https://coop.noegosunderwater.com
2. Tap the **⋮** menu
3. Tap **Install app** or **Add to Home screen**

The icon now lives on your home screen and opens full-screen, no browser chrome.

## Trouble Signing In?

- **"Invalid username or code"** — double-check the username (it's case-insensitive but make sure it's the one Travis approved). Check that your authenticator code hasn't expired (it changes every 30 seconds).
- **Lost your phone / authenticator app** — talk to Travis. He can revoke your old TOTP and issue a new setup link.
- **Forgot your username** — Travis can look it up.
- **The page is broken or you can't get past login** — text Travis with what you see and he'll dig in.
