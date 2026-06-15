# NCCI Procedure-to-Procedure (PTP) Edits

> Illustrative reference text for demonstration. Modeled on public CMS National
> Correct Coding Initiative concepts. Not an authoritative or current copy of CMS
> policy. Replace with the official CMS NCCI Policy Manual for real use.

## Purpose

Procedure-to-procedure (PTP) edits identify pairs of HCPCS or CPT codes that
should not both be reported for the same patient by the same provider on the same
date of service. One code in the pair is the Column One (comprehensive) code and
the other is the Column Two code. When an edit applies, the Column Two code is
denied unless an appropriate modifier is appended and supported.

## Modifier indicators

Every PTP edit carries a modifier indicator that controls whether the pair can be
unbundled:

- Indicator 0 means a modifier is not allowed. The two codes can never be reported
  together for the same date of service. No modifier overrides the edit, and the
  Column Two code will be denied.
- Indicator 1 means a modifier is allowed. The codes are normally bundled, but an
  appropriate modifier on the Column Two code may allow separate payment when the
  services were genuinely distinct and the documentation supports it.
- Indicator 9 means the edit is not applicable, typically because it has been
  deleted. No action is required.

## How edits are applied

Claims processing compares each pair of codes on a claim against the active edit
table. Because edits are directional, a pair is checked in both orderings. An edit
with a deletion date in the past no longer applies. Reporting a bundled Column Two
code without a supported modifier results in denial of that line.

## Modifiers that may bypass an indicator-1 edit

The distinct procedural service modifier 59 and the more specific X modifiers
(XE, XS, XP, XU) may bypass an indicator-1 edit when the services were separate.
XE is a separate encounter, XS is a separate structure or organ, XP is a separate
practitioner, and XU is an unusual non-overlapping service. A modifier should be
appended only when the medical record substantiates the distinct service.
