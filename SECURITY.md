# Security policy

## Scope

FLOC*Loom installs custom-agent instructions and runs shell/Python verification
helpers. Treat the plugin, its marketplace source, the installed agent files, and the
Codex model configuration as a supply-chain boundary.

Use a signed release tag or immutable commit when installing a trusted route. Do not
use a moving branch for production or security-sensitive work.

The execution ledger is evidence, not a cryptographic attestation. A host-level
read-only sandbox is authoritative; behavioral read-only mode must be reported as
residual risk and is never equivalent to OS-enforced isolation.

## Reporting a vulnerability

Do not open a public issue for an undisclosed vulnerability. Contact the maintainer
through the security contact configured for the repository with:

- affected release or commit;
- reproduction steps and impact;
- relevant logs or ledger artifacts after removing credentials and private prompts;
- a proposed mitigation, if available.

Never include API keys, access tokens, private rollout contents, or customer data in a
report.
