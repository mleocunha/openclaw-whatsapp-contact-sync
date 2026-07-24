# OpenClaw WhatsApp Contact Sync

Community patch for keeping a local WhatsApp contact store synchronized from the **same Baileys session already used by the OpenClaw WhatsApp plugin**.

The project avoids a second WhatsApp Web pairing. It patches the installed OpenClaw WhatsApp plugin so its existing socket listens for:

- `messaging-history.set`
- `contacts.upsert`
- `contacts.update`

The collected contacts are persisted locally at:

```text
~/.openclaw/baileys_store.json
```

## Why this exists

OpenClaw can connect to WhatsApp and send messages, but its configured directory is not necessarily a complete mirror of the contacts known by Baileys. A separate synchronization script can collect those contacts, but opening a second Baileys socket creates another pairing and may cause WhatsApp session conflicts.

This project concentrates message transport and contact synchronization in the **single OpenClaw pairing**.

## Status

Experimental community solution, initially validated with:

- OpenClaw `2026.7.1-2`
- OpenClaw WhatsApp plugin `2026.7.1`
- Baileys `7.0.0-rc13`
- macOS on Apple Silicon

The patch modifies compiled plugin files under `~/.openclaw/extensions/whatsapp/dist`. OpenClaw or plugin updates may overwrite it.

## Installation

### 1. Clone the repository

```bash
git clone https://github.com/mleocunha/openclaw-whatsapp-contact-sync.git
cd openclaw-whatsapp-contact-sync
```

### 2. Stop the OpenClaw gateway

```bash
openclaw gateway stop
```

### 3. Back up the WhatsApp plugin

```bash
cp -a ~/.openclaw/extensions/whatsapp \
  ~/.openclaw/extensions/whatsapp.backup-$(date +%Y%m%d-%H%M%S)
```

### 4. Apply the patch

```bash
python3 patch_whatsapp_contact_sync.py
```

Expected output:

```text
Patch applied successfully.
File:   /Users/.../.openclaw/extensions/whatsapp/dist/session-....js
Backup: /Users/.../.openclaw/extensions/whatsapp/dist/session-....js.bak-...
```

### 5. Confirm the patch

```bash
grep -Rni \
  'OPENCLAW_CONTACT_SYNC_PATCH_V1\|syncFullHistory:' \
  ~/.openclaw/extensions/whatsapp/dist/session-*.js
```

The result should include:

```text
syncFullHistory: true,
OPENCLAW_CONTACT_SYNC_PATCH_V1
```

### 6. Start OpenClaw and pair WhatsApp

```bash
openclaw gateway start
sleep 5
openclaw channels login --channel whatsapp
```

Scan the QR code through **WhatsApp → Linked devices → Link a device**. This is the only pairing needed.

After linking, leave the gateway running for a few minutes so the history and contact events can arrive.

### 7. Verify the contact store

```bash
node - <<'NODE'
const fs = require('fs');
const file = process.env.HOME + '/.openclaw/baileys_store.json';

if (!fs.existsSync(file)) {
  console.error('Contact store not found:', file);
  process.exit(1);
}

const data = JSON.parse(fs.readFileSync(file, 'utf8'));
const contacts = Object.values(data.contacts || {});

console.log('File:', file);
console.log('Contacts:', contacts.length);
console.log('Updated at:', data.updatedAt);
console.log('Last event:', data.lastReason);
console.table(contacts.slice(0, 10));
NODE
```

## Output format

```json
{
  "generatedAt": "2026-07-24T00:00:00.000Z",
  "updatedAt": "2026-07-24T00:00:10.000Z",
  "source": "openclaw-whatsapp",
  "lastReason": "messaging-history.set",
  "contacts": {
    "5561XXXXXXXX@s.whatsapp.net": {
      "id": "5561XXXXXXXX@s.whatsapp.net",
      "name": "Contact name",
      "notify": "WhatsApp profile name",
      "verifiedName": ""
    }
  }
}
```

The file may contain personal data. Never commit it.

## Reapplying after updates

Check whether the marker still exists:

```bash
grep -R \
  'OPENCLAW_CONTACT_SYNC_PATCH_V1' \
  ~/.openclaw/extensions/whatsapp/dist/session-*.js
```

When the marker is absent:

```bash
openclaw gateway stop
python3 patch_whatsapp_contact_sync.py
openclaw gateway start
```

The patcher is idempotent: it refuses to apply the same marker twice.

## Rollback

The patcher creates a timestamped backup beside the modified session file. To roll back:

```bash
openclaw gateway stop
```

Locate the files:

```bash
ls -1 ~/.openclaw/extensions/whatsapp/dist/session-*.js*
```

Restore the desired backup over the patched file, then restart:

```bash
cp ~/.openclaw/extensions/whatsapp/dist/session-....js.bak-TIMESTAMP \
   ~/.openclaw/extensions/whatsapp/dist/session-....js

openclaw gateway start
```

Restoring the complete plugin backup is also possible:

```bash
rm -rf ~/.openclaw/extensions/whatsapp
cp -a ~/.openclaw/extensions/whatsapp.backup-TIMESTAMP \
      ~/.openclaw/extensions/whatsapp
```

## Privacy and security

Do not publish or commit:

- `baileys_store.json`
- WhatsApp authentication directories
- OpenClaw configuration containing tokens
- QR codes
- session credentials
- contact exports

The included `.gitignore` blocks common local artifacts, but users remain responsible for reviewing every commit.

## Compatibility warning

This is not an official OpenClaw, WhatsApp, Meta, Baileys, Google, or OpenAI project. Internal OpenClaw bundle names and implementation details can change without notice. Review the generated backup and patch result before operational use.

## How this solution was developed

This solution emerged from iterative troubleshooting and experimentation by **Mauro Leonardo Cunha**, using both **Google Gemini** and **OpenAI ChatGPT** as collaborative AI tools. Gemini helped develop the initial standalone Baileys contact synchronization workflow; subsequent analysis and experimentation with ChatGPT led to consolidating synchronization into the single WhatsApp pairing already managed by OpenClaw.

The resulting implementation reflects human judgment, testing, correction of failed paths, and contributions from both AI-assisted workstreams.

## Contributing

Issues, compatibility reports, safer patching strategies, tests, and improvements are welcome. Please remove all phone numbers, contact names, credentials, tokens, and session data from reports.

## License

Released under the **BSD Zero Clause License (0BSD)**. You may use, copy, modify, and distribute the code without attribution requirements. See [`LICENSE`](LICENSE).
