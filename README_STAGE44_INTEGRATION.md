# Stage 44 integration candidate

This candidate applies the planning integration patch to the extracted `feature-affiliate-v2-validation` source snapshot and adds a read-only operations dashboard. `run_batch` returns editorial planning and operations reporting; the local CLI can write a standalone HTML report using `--dashboard-html`.

The scheduled GitHub Actions workflow now appends a privacy-safe run summary from its JSON report, with a static fallback if the report is missing or invalid. It contains only processed count, status counts, and review/metrics limitations. It does not expose article titles, body text, API credentials, or affiliate URLs. It does not change the workflow trigger or post content to WordPress.

A separate offline regression workflow is configured for pushes and pull requests targeting `feature-affiliate-v2-validation`. It runs tests on Python 3.11 and 3.12 with `contents: read`, and does not receive API or WordPress secrets. YAML was parsed locally; the workflow itself has not run on GitHub because this snapshot has not been pushed.

## Verification status

- Full offline suite after the latest summary change: **581 passed**, 1 third-party pytest deprecation warning (Python 3.12).
- Markdown-specific tests: 3 passed. Dashboard integration tests: 5 passed. Both workflow YAML files parsed successfully.
- The five-item dry-run uses mocked external services and confirms no WordPress write. Real APIs, WordPress, GA4, Search Console, affiliate revenue, and long-duration operation remain untested.
- This candidate is now prepared in a Git checkout of feature-affiliate-v2-validation based on 8c64405. main remains unchanged. See the session report for remote push status.

History integrity: malformed history and duplicate/missing keys now stop reads/writes instead of treating corruption as a first run. Nine new local and mocked GitHub cases pass. The offline CI installs PyYAML explicitly.
