# A-CDM primary study update, 19 November 2026

Every row of ACDM_Berlin_Primary_With_OpenSky_Check.csv originates in a finalized BER A-CDM snapshot. OpenSky supplies only prefixed departure cross-check columns in this table. Missing/ambiguous matches remain explicit and never create A-CDM records. Summary counts and matching limitations are in summary.json.

The primary unit is a departure record. These observations cannot be represented as complete landing-to-next-takeoff or AIBT–AOBT pairs because the source lacks arrival/block milestones. TOBT/TSAT are target values and their differences from ATOT are not measured queue or service durations. Raw timestamps retain their unverified naive timezone.

The previous10,940 aircraft-pair dataset originates in OpenSky. Only826 core pairs have candidate A-CDM reference links. It is a separate auxiliary reconstruction and cannot become A-CDM data by renaming columns. Previous OCPN/Promenade outputs and60 replications are an exploratory pilot using that reconstruction. They are not new A-CDM-only calibrated results.

This version does not overwrite earlier source/prepared files or experimental outputs. Technical checks verify source JSON/CSV consistency, manifest counts and raw hashes. OpenSky cross-check tests UTC/Berlin hypotheses within30minutes, retains ambiguity, prohibits reused unique matches and reports agreement conditional on the retained candidates.
