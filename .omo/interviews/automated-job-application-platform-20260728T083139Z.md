# Automated Job Application Platform — Interview Summary

Profile: standard  
Context: greenfield  
Rounds: 8  
Final ambiguity: 19% (threshold: 20%)

1. Submit every selected job using browser automation, including external forms.
2. Infer seniority from CV; employment types configurable.
3. Job title, location, and remote preference configurable.
4. Submit immediately after ranking; no final approval step.
5. Pause unknown/ambiguous questions; user answers in UI; reuse saved answers.
6. Source CV from Overleaf through `.keys/` credentials.
7. Tailoring runs automatically.
8. Keep tailoring conservative: no invented education/certifications. Missing facts require confirmation and persist for reuse.

External constraints confirmed: JobSpy MCP discovers/reads jobs only; Composio Gmail reads/tracks email only. Neither submits applications. Submission needs a separate browser-automation adapter. CAPTCHA, MFA, or site blocks must queue manual intervention rather than bypass safeguards.
