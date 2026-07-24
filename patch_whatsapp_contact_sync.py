#!/usr/bin/env python3
"""Patch the installed OpenClaw WhatsApp plugin to persist Baileys contacts.

The patch reuses the socket already opened by the OpenClaw WhatsApp plugin,
thereby avoiding a second WhatsApp Web pairing and session conflicts.
"""

from __future__ import annotations

import shutil
import sys
import time
from pathlib import Path

MARKER = "OPENCLAW_CONTACT_SYNC_PATCH_V1"
SESSION_GLOB = "session-*.js"


def fail(message: str) -> None:
    print(f"Error: {message}", file=sys.stderr)
    raise SystemExit(1)


def main() -> None:
    dist_dir = Path.home() / ".openclaw/extensions/whatsapp/dist"

    if not dist_dir.is_dir():
        fail(f"OpenClaw WhatsApp dist directory not found: {dist_dir}")

    candidates: list[tuple[Path, str]] = []

    for file_path in dist_dir.glob(SESSION_GLOB):
        try:
            text = file_path.read_text(encoding="utf-8")
        except OSError as exc:
            fail(f"could not read {file_path}: {exc}")

        if "makeWASocket({" in text and "syncFullHistory:" in text:
            candidates.append((file_path, text))

    if len(candidates) != 1:
        print(
            "Error: expected exactly one compiled WhatsApp session file "
            f"but found {len(candidates)}.",
            file=sys.stderr,
        )
        for file_path, _ in candidates:
            print(f"  {file_path}", file=sys.stderr)
        raise SystemExit(1)

    session_file, text = candidates[0]

    if MARKER in text:
        print(f"Patch already present: {session_file}")
        return

    old_sync = "syncFullHistory: false,"
    if old_sync not in text:
        fail("could not find 'syncFullHistory: false,'; plugin layout may have changed")

    anchor = (
        'sock.ev.on("creds.update", () => '
        "enqueueSaveCreds(authDir, saveCreds, sessionLogger));"
    )
    if anchor not in text:
        fail("could not find the insertion point after the creds.update listener")

    first_import_end = text.find("\n")
    if first_import_end == -1:
        fail("could not locate the first import statement")

    backup = session_file.with_suffix(
        session_file.suffix + f".bak-{int(time.time())}"
    )
    shutil.copy2(session_file, backup)

    imports = (
        'import fs from "node:fs";\n'
        'import path from "node:path";\n'
    )
    text = text[: first_import_end + 1] + imports + text[first_import_end + 1 :]
    text = text.replace(old_sync, "syncFullHistory: true,", 1)

    patch = r'''
	// OPENCLAW_CONTACT_SYNC_PATCH_V1
	const contactStorePath = path.join(
		process.env.HOME,
		".openclaw",
		"baileys_store.json"
	);

	let contactStore = {
		generatedAt: null,
		updatedAt: null,
		source: "openclaw-whatsapp",
		contacts: {}
	};

	try {
		if (fs.existsSync(contactStorePath)) {
			const loaded = JSON.parse(
				fs.readFileSync(contactStorePath, "utf8")
			);

			if (loaded && typeof loaded === "object") {
				contactStore = {
					...contactStore,
					...loaded,
					contacts:
						loaded.contacts &&
						typeof loaded.contacts === "object"
							? loaded.contacts
							: {}
				};
			}
		}
	} catch (error) {
		sessionLogger.warn?.(
			`WhatsApp contact store could not be loaded: ${error.message}`
		);
	}

	let contactStoreWriteTimer;

	const persistContactStore = (reason) => {
		clearTimeout(contactStoreWriteTimer);

		contactStoreWriteTimer = setTimeout(() => {
			try {
				const now = new Date().toISOString();

				contactStore.generatedAt ??= now;
				contactStore.updatedAt = now;
				contactStore.lastReason = reason;

				fs.mkdirSync(path.dirname(contactStorePath), {
					recursive: true
				});

				const temporaryPath = `${contactStorePath}.tmp`;

				fs.writeFileSync(
					temporaryPath,
					JSON.stringify(contactStore, null, 2),
					"utf8"
				);

				fs.renameSync(temporaryPath, contactStorePath);

				sessionLogger.info?.(
					`WhatsApp contacts persisted: ${
						Object.keys(contactStore.contacts).length
					} contacts (${reason})`
				);
			} catch (error) {
				sessionLogger.error?.(
					`WhatsApp contact store could not be saved: ${error.message}`
				);
			}
		}, 750);
	};

	const rememberContacts = (contacts, reason) => {
		if (!Array.isArray(contacts)) return;

		let changed = 0;

		for (const contact of contacts) {
			const id = contact?.id;

			if (
				typeof id !== "string" ||
				!(
					id.endsWith("@s.whatsapp.net") ||
					id.endsWith("@lid")
				)
			) {
				continue;
			}

			const existing = contactStore.contacts[id] ?? {};

			contactStore.contacts[id] = {
				...existing,
				id,
				name:
					contact.name ||
					existing.name ||
					contact.notify ||
					contact.verifiedName ||
					"",
				notify:
					contact.notify ||
					existing.notify ||
					"",
				verifiedName:
					contact.verifiedName ||
					existing.verifiedName ||
					""
			};

			changed++;
		}

		if (changed > 0) {
			persistContactStore(reason);
		}
	};

	sock.ev.on("contacts.upsert", (contacts) => {
		rememberContacts(contacts, "contacts.upsert");
	});

	sock.ev.on("contacts.update", (updates) => {
		rememberContacts(updates, "contacts.update");
	});

	sock.ev.on("messaging-history.set", ({ contacts }) => {
		rememberContacts(contacts, "messaging-history.set");
	});
'''

    text = text.replace(anchor, anchor + "\n" + patch, 1)

    try:
        session_file.write_text(text, encoding="utf-8")
    except OSError as exc:
        shutil.copy2(backup, session_file)
        fail(f"could not write the patched file; backup restored: {exc}")

    print("Patch applied successfully.")
    print(f"File:   {session_file}")
    print(f"Backup: {backup}")


if __name__ == "__main__":
    main()
