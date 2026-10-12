# Baseline vs freshly optimized candidate profiles

Compares the extracted `original_profile` for every candidate in the baseline against the latest rerun in `optimized/candidate_profile`. Each CSV row is a differing field; arrays are compared by index. `Missing from optimized` means the old field/value is absent at that path in the new parse, while `Value changed` means both sides have different values. Review the source resume before treating any difference as information loss.

- Candidate profiles compared: 16
- Differing field paths: 1212
- Missing from optimized: 397
- Added in optimized: 295
- Value changed: 520
- Detailed table: [candidate_profile_comparison.csv](./candidate_profile_comparison.csv)

| Candidate ID | Missing from optimized | Added in optimized | Value changed |
|---|---:|---:|---:|
| CAN_18CF07232472 | 0 | 0 | 1 |
| CAN_1CA3DA4F0062 | 24 | 20 | 17 |
| CAN_2325AD0B18CE | 39 | 36 | 47 |
| CAN_410B14422E90 | 23 | 7 | 28 |
| CAN_4CFB167D7487 | 31 | 12 | 45 |
| CAN_5441F5865D9B | 6 | 4 | 13 |
| CAN_572F92BAB63C | 30 | 21 | 40 |
| CAN_5DB428DE94C1 | 24 | 25 | 24 |
| CAN_6EEC4CAA4B86 | 0 | 0 | 1 |
| CAN_79F428525AFE | 34 | 35 | 27 |
| CAN_7B72257C5D85 | 35 | 30 | 42 |
| CAN_81791789C6AA | 36 | 12 | 48 |
| CAN_B67DE2B9BADB | 9 | 17 | 13 |
| CAN_C5D1338F49C1 | 41 | 15 | 70 |
| CAN_CB63A04EDA0B | 27 | 28 | 50 |
| CAN_E3036E1C2BDA | 38 | 33 | 54 |

## Differences by profile section

| Section | Missing from optimized | Added in optimized | Value changed |
|---|---:|---:|---:|
| certifications | 0 | 0 | 5 |
| education | 0 | 1 | 10 |
| experience | 1 | 3 | 65 |
| metadata | 0 | 0 | 16 |
| personal_information | 0 | 0 | 9 |
| skills | 396 | 291 | 415 |
