# Credit Report Studio + Consumer-Report Dispute Copilot

This project has two deliberately separate parts:

1. A private dashboard for factual profile information, scores, report marks,
   evidence questions, and dispute-plan exports.
2. A local Playwright copilot for the three nationwide bureaus and eight
   specialty-report sources that waits for manual login and never submits a
   dispute for you.

## Dashboard

```sh
npm install
npm start
```

Open `http://localhost:4173`. Data is stored in that browser's `localStorage`,
not on the server. Do not enter an SSN, password, security answer, or complete
account number.

The dashboard displays scores only when you enter both the number and model.
Base FICO and VantageScore values are not interchangeable. FICO Auto Scores are
industry-specific and can range from 250–900. Credit-based insurance scores are
different again, are insurer/state dependent, and cannot be calculated here.

The tool does not invent projected point increases. You may record a range only
when it came from a named score simulator or lender tool; it remains a scenario,
not a prediction.

Text-based PDF reports can be opened in the Upload reports tab. Extraction runs
in the visitor's browser and does not send the PDF to the Render server. The
result is a candidate list, not a finding that an item is wrong. After the user
records factual evidence and marks an item inaccurate or incomplete, the
Letters & instructions tab creates an editable dispute letter and links to the
agency's official filing channel. The user must verify, sign, and submit it.

For extracted accounts, the simplified workflow offers three per-account
choices: not recognized, identity theft/fraud, or accurate/skip. The first two
prefill the factual reason and create the appropriate letter and instructions.
The fraud path links to IdentityTheft.gov and reminds the user to contact the
creditor's fraud department. There is intentionally no bulk "dispute all"
control because each identity-theft statement must be true for that account.

## Consumer-report copilot

Add report marks in the dashboard. Only items marked factually inaccurate or
incomplete with a dispute reason can be exported. Save the download over the
local `disputes.json`, then run:

```sh
npm run bot
```

The copilot supports Experian, TransUnion, Equifax, Innovis, LexisNexis Risk
Solutions, ChexSystems, Early Warning Services, Experian Clarity Services,
DataX, Teletrack, and NCTUE. Log in manually when an online portal is available.
It prepares fields only when it can identify them unambiguously, guides you to
the agency's official document/support channel otherwise, and always stops
before submission. Teletrack is retained as a report-source label but its
official consumer site now routes consumers to DataX.

Specialty reports are not displayed as ordinary FICO scores. Their data may be
used for banking, insurance, telecom/utility, identity, or non-prime lending
decisions, depending on the agency and the report product.

## Render

The dashboard can be hosted on Render with `render.yaml`. Because all profile
and report data stays in the visitor's browser storage, the Render server does
not receive it. Render requires private `APP_USERNAME` and `APP_PASSWORD`
environment variables; if either is absent, the hosted service refuses access.
Use a unique password and rely on Render's HTTPS endpoint.

The Playwright copilot does not run inside this Render web service. A remote
browser would need an authenticated bureau session cookie, which is equivalent
to login access; CAPTCHA/MFA can also require direct interaction. Do not upload
cookies, passwords, SSNs, or report PDFs to this deployment. The final dispute
review and attestation remain manual on your computer.

## Important limitation

Only dispute information you genuinely believe is inaccurate or incomplete.
Accurate negative marks should not be disputed. This is an organizational and
form-preparation tool, not legal advice, a credit score, or a credit-repair
service.
