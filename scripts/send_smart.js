#!/usr/bin/env node

import fs from 'node:fs';
import path from 'node:path';
import { spawnSync } from 'node:child_process';

const storePath = path.join(
  process.env.HOME,
  '.openclaw',
  'baileys_store.json'
);

const targetName = process.argv[2]?.trim();
const messageText = process.argv[3];

if (!targetName || !messageText) {
  console.error('Usage: node send_smart.js "Name" "Message"');
  process.exit(1);
}

if (!fs.existsSync(storePath)) {
  console.error(`Contact store not found: ${storePath}`);
  process.exit(1);
}

let contacts;
try {
  const data = JSON.parse(fs.readFileSync(storePath, 'utf8'));
  contacts = Object.values(data.contacts || {});
} catch (error) {
  console.error(`Could not read contact store: ${error.message}`);
  process.exit(1);
}

const search = targetName.toLocaleLowerCase();
const matches = contacts.filter((contact) => {
  const fields = [
    contact.name,
    contact.notify,
    contact.verifiedName,
    contact.id
  ];

  return fields.some((value) =>
    String(value || '')
      .toLocaleLowerCase()
      .includes(search)
  );
});

if (matches.length === 0) {
  console.error(`No contact found for: ${targetName}`);
  process.exit(1);
}

if (matches.length > 1) {
  console.error(
    `AMBIGUITY: found ${matches.length} contacts for "${targetName}".`
  );

  matches.forEach((contact, index) => {
    const displayName =
      contact.name ||
      contact.notify ||
      contact.verifiedName ||
      'Unnamed contact';

    console.error(
      `  ${index + 1}. ${displayName} (${contact.id})`
    );
  });

  process.exit(2);
}

const contact = matches[0];
const targetJid = contact.id;
const displayName =
  contact.name ||
  contact.notify ||
  contact.verifiedName ||
  targetJid;

console.log(`Unique contact identified: ${displayName} (${targetJid})`);

const result = spawnSync(
  'openclaw',
  [
    'message',
    'send',
    '--channel',
    'whatsapp',
    '--target',
    targetJid,
    '--message',
    messageText
  ],
  {
    stdio: 'inherit',
    encoding: 'utf8'
  }
);

if (result.error) {
  console.error(`Could not start OpenClaw: ${result.error.message}`);
  process.exit(1);
}

process.exit(result.status ?? 1);
