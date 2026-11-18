# Surepass Sandbox Access Verification (`2026-11-18`)

- **URL:** `https://surepass.io/` -> `Get API Key` form & `https://docs.surepass.io`
- **Observed Behaviour (`verified`):**
  1. Submitting the "Get API Key" form on `surepass.io` does **not** issue an instant self-serve API token; it displays: *"Thank you! Your request has been received successfully. One of our experts will call you within the next 5 minutes."*
  2. Probing `https://docs.surepass.io` returns HTTP `200`, redirecting to **`https://console.surepass.app/?_source=docs&_return_to=https%3A%2F%2Fapp.surepass.app%2Fdocs%2Fkyc`** (login-gated developer console).
  3. **Inside `console.surepass.app` (after signing in on `2026-11-18`):** `Sandbox | Production` toggle, `API Catalogue`, and `API Documentation` are disabled, and opening the catalogue displays:
     > *"API Catalogue Access Restricted — Your environment has not been approved for API catalogue access yet. Please contact your account manager to get access."*
  4. `https://sandbox.surepass.io` returns `404`; `https://app.surepass.io` times out (`ReadTimeout`); `https://developer.surepass.io` fails to connect (`ConnectError`).
- **Implication:** Both Surepass's **sandbox** and its **API catalogue/documentation** are **account-manager-approval-gated** (not self-serve), unlike `data.gov.in` (instant self-serve API key) or `api.gleif.org` (unauthenticated CC0 REST API).
- **What remains `undetermined`:** No live call was made to `kyc-api.surepass.io` in this submission. Whether the sandbox returns live vs. mock responses, its call limits, expiry, and whether IFSC/LEI/GST endpoints are included in the free tier remain `undetermined` pending account-manager approval.
- **What remains `undetermined`:** No live call was made to `kyc-api.surepass.io` in this submission. Whether the sandbox returns live vs. mock responses, its call limits, expiry, and whether IFSC/LEI/GST endpoints are included in the free tier remain `undetermined`.
