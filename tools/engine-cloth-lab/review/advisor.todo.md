- [x] Route through the **how** skill. For motivation questions, also route through the **why** skill.
  - skip: nested explorers. This agent is the independent reviewer in the parent exploration. Scope stays read-only except review artifacts.
- [x] Throughput checkpoint stays one line: `throughput checkpoint: n/a, read-only investigation`.
- [x] Produce the `how`-shaped output (Overview / Key Concepts / How It Works / Where Things Live / Gotchas), or a recommendation with a tradeoffs table if the request is a decision between alternatives.
- [x] Apply the **unslop** skill to the reply.
- [x] Read canonical input and installed engine declarations.
- [x] Save architecture judgment and independent acceptance checklist.
- [x] Review the candidate artifact supplied by parent.
- [x] Recheck R01-R07 against the updated candidate and preserve first-round failures.
- [x] Run 12 independent Node checks and record candidate hashes.
- [ ] Independently operate the final HTML in a browser.
  - BLOCKED: local Chromium socket creation denied; Playwright MCP connection unavailable. Parent browser verification remains separate evidence.

throughput checkpoint: n/a, read-only investigation
