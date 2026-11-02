# Code signing policy

Status: free application submitted on 2 November 2026; the maintainer reports the receipt confirmation after completing the CAPTCHA. Admission pending, not approved. No LBR release has been signed by SignPath Foundation. The unsigned RC is publicly available at https://github.com/tiikonic420/LBR-DJ-Library-Manager/releases/tag/v5.0.0-rc10 . See Documentation/SUIVI_SIGNPATH.md for evidence and limits.

Planned attribution, only if accepted: Free code signing provided by SignPath.io, certificate by SignPath Foundation.

## Scope

Request signing only for our own launcher built from Build/Launcher.cs and our MSI assembled from the reviewed source commit on GitHub-hosted Windows runners. Python, Microsoft system runtime files, and third-party native libraries keep their upstream signatures or unsigned state; this project will not sign third-party binaries as its own.

The MSI must contain the signed launcher, not the earlier unsigned executable. Final manifests and portable archives must be generated after signing. SignPath artifact settings must enforce the allowed paths and reviewed product/version metadata. Current PE 5.0.10.1 and MSI 5.0.10 use different version formats; their mapping and product names require explicit agreement in the signing configuration before activation.

Each release requires manual signing approval. Committer, reviewer and manual signing approver: tiikonic420, confirmed on 2 November 2026. GitHub MFA enabled according to the maintainer; SignPath account roles and MFA will be configured only if admitted. See GOVERNANCE.md. No credentials or signing certificates are included in this repository.

## Privacy

See PRIVACY.md for local processing and explicitly requested network operations. No acceptance, signing service or public reputation is claimed by this policy draft.
