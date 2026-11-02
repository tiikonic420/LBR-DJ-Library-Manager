# SignPath application — draft, not submitted

PUBLICATION PREPARATION COMPLETE; NOT SUBMITTED. While the repository is private, the links below cannot serve as public application evidence. No application has been submitted. Public visibility and a public RC release require a later explicit owner instruction.

Project: LBR DJ Library Manager
Maintainer GitHub account: tiikonic420
Repository: https://github.com/tiikonic420/LBR-DJ-Library-Manager (currently private)
Public release: [UNSIGNED_RC_RELEASE_URL]
License: GPL-3.0-or-later for original LBR code, with original third-party licenses preserved; https://github.com/tiikonic420/LBR-DJ-Library-Manager/blob/main/LICENSE (currently private) and https://github.com/tiikonic420/LBR-DJ-Library-Manager/blob/main/LICENSING.md (currently private).
Build workflow and successful run: https://github.com/tiikonic420/LBR-DJ-Library-Manager/blob/main/.github/workflows/validation-windows.yml (currently private) / https://github.com/tiikonic420/LBR-DJ-Library-Manager/actions/runs/41406418487 (success; currently private)
Code signing policy: https://github.com/tiikonic420/LBR-DJ-Library-Manager/blob/main/CODE_SIGNING_POLICY.md (currently private)
Privacy policy: https://github.com/tiikonic420/LBR-DJ-Library-Manager/blob/main/PRIVACY.md (currently private)

LBR DJ Library Manager is a Windows desktop application for managing DJ audio metadata, artwork and playlist workflows. It integrates Tag Studio, MusicGenre, RekordSync and Rekordbox-to-Serato tools, with optional backup and integrity controls. It is independent of AlphaTheta/Pioneer DJ and Serato and does not claim their endorsement.

We would like to apply for SignPath Foundation's free open-source signing program. Our own Windows launcher is built from C# source; the per-user MSI is assembled from our build scripts. We intend to submit only artifacts built from reviewed commits on GitHub-hosted Windows runners. We will not sign Python, Microsoft runtime components or other upstream binaries as our own. Each release signing request will require manual maintainer approval.

The existing unsigned 5.0 RC R10 was tested locally on Windows using synthetic audio and isolated libraries. Installation, file integrity, backup/restore and uninstall passed in Windows Sandbox, but VerifiedAndReputableDesktop application control blocked the unsigned launcher (WinError 4551). The release remains an RC; MSI ICE validation and real DJ-application reopen tests on synthetic libraries remain open.

The project has been developed with GPT assistance. On 2 November 2026, the maintainer confirmed, to the best of their knowledge, the rights to publish LBR's original code and artwork under GPL-3.0-or-later while preserving dependency licenses. This is the maintainer's declaration, not an independent legal audit; third-party notices and redistribution obligations are recorded in Documentation/REVUE_LICENCES.md, including the separate Windows system-runtime terms.

This is a newly published project [ONLY AFTER PUBLICATION; otherwise do not submit]. We do not yet claim an established public user base, third-party reputation or contributor history. Please advise whether the project is currently eligible or which verifiable public evidence would be required. We understand that approval is discretionary and not guaranteed by the presence of a public repository.

GitHub MFA enabled: confirmed by the maintainer on 2 November 2026. Committer, reviewer and signing approver: tiikonic420, confirmed on 2 November 2026. The same maintainer holds all three roles; no independent second reviewer is claimed. SignPath account roles and MFA will be configured if admitted.

Build evidence: the GitHub-hosted Windows run above passed all 17 suites, 105 unittest cases without skips, six additional GUI scenarios, and all seven audio tests, then built an unsigned MSI. Its embedded files were checked locally against the manifest. The exact CI MSI (SHA256 86dceabb773f6d8d601b3dcbc56d1dfacf40dead517deb8b4ca87e5fe6a00228) was subsequently tested: installed GUI launch, Explorer drag-and-drop of two synthetic WAVs, tag writing, integrity verification, restoration and uninstall passed on the maintainer PC. All 23 fictitious files remained byte-identical across uninstall. Sandbox installation, payload integrity, module-level backup/restore and uninstall passed, but its launcher was blocked with WinError 4551. Sandbox GUI and mutex remain unexecuted; no Windows protection was bypassed. See Documentation/ESSAI_MSI_GITHUB.md.

Technical license review: original LBR code GPL-3.0-or-later, upstream licenses retained. The initial unsigned release package includes the exact CI-built MSI, complementary native dependency notices and corresponding project sources. No upstream binary is to be signed as our own.
