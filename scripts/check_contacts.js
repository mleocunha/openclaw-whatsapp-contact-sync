#!/usr/bin/env node

import fs from 'node:fs';
import path from 'node:path';

const storePath = path.join(
  process.env.HOME,
  '.openclaw',
  'baileys_store.json'
);

const query = process.argv.slice(2).join(' ').trim();

if (!query) {
  console.log(JSON.stringify({
    status: 'error',
    message: 'No contact name supplied'
  }));
  process.exit(1);
}

if (!fs.existsSync(storePath)) {
  console.log(JSON.stringify({
    status: 'no_store',
    message: 'Baileys contact store not found',
    path: storePath
  }));
  process.exit(0);
}

try {
  const data = JSON.parse(fs.readFileSync(storePath, 'utf8'));
  const contacts = Object.values(data.contacts || {});
  const normalizedQuery = query.toLocaleLowerCase();

  const matches = contacts
    .filter((contact) => {
      const fields = [
        contact.name,
        contact.notify,
        contact.verifiedName,
        contact.id
      ];

      return fields.some((value) =>
        String(value || '')
          .toLocaleLowerCase()
          .includes(normalizedQuery)
      );
    })
    .map((contact) => ({
      name:
        contact.name ||
        contact.notify ||
        contact.verifiedName ||
        'Unnamed contact',
      jid: contact.id,
      phone: String(contact.id || '').split('@')[0],
      notify: contact.notify || '',
      verifiedName: contact.verifiedName || ''
    }));

  console.log(JSON.stringify({
    status: 'success',
    query,
    count: matches.length,
    contacts: matches
  }, null, 2));
} catch (error) {
  console.log(JSON.stringify({
    status: 'error',
    message: error.message
  }));
  process.exit(1);
}
