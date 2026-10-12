# Old vs optimized resume comparison

Compares the extracted values by meaning, rather than raw JSON structure. Removed values appear in the baseline but not in the optimized parse; added values appear in the optimized parse but not the baseline. Differences need source-resume review before being called regressions.

**Profiles:** 16 | **Scoring cases:** 15 | **Changed extraction areas:** 38

## Extraction changes

| Candidate | Section | Count (old -> optimized) | Removed from optimized | Added in optimized |
|---|---|---:|---|---|
| CAN_1CA3DA4F0062 | Experience | 1 -> 1 | HR Intern; People Bridge; Jan 2026 to Apr 2026; 4 months; Screened resumes, scheduled interviews and updated candidate records in HRMS.; Prepared Excel reports for recruitment activity. | HR Intern; PeopleBridge; Jan 2026 to Apr 2026; 4 months; Screened resumes, scheduled interviews and updated candidate records in HRMS.; Prepared Excel reports for recruitment activity. |
| CAN_2325AD0B18CE | Skills | 13 -> 13 | Applicant Tracking System | Customer Relationship Management |
| CAN_2325AD0B18CE | Experience | 2 -> 2 | Senior HR Manager; People Works Technologies; Jan 2020 to Present; 81 months; Managed recruitment and talent acquisition activities.; Coordinated payroll and employee relations processes.; Maintained HRMS records and HR reports using MS Excel.; Jun 2018 to ... | Senior HR Manager; PeopleWorks Technologies; Jan 2020 to Present; 82 months; Managed recruitment and talent acquisition activities.; Coordinated payroll and employee relations processes.; Maintained HRMS records and HR reports using MS Excel.; HR Executive;... |
| CAN_410B14422E90 | Skills | 7 -> 8 | - | API |
| CAN_410B14422E90 | Education | 1 -> 1 | Degree: Bachelor of Technology; Field: Information Technology; Year: 2019 | Degree: Bachelor of Technology; Field: Information Technology; University: KTU; Year: 2019 |
| CAN_410B14422E90 | Experience | 1 -> 1 | Backend Engineer; Enterprise Soft; Jan 2020 to Present; 81 months; Developed Python backend services and database integrations.; Built APIs using Flask and maintained MySQL databases.; Used Docker and Git in team development. | Backend Engineer; EnterpriseSoft; Jan 2020 to Present; 82 months; Developed Python backend services and database integrations.; Built APIs using Flask and maintained MySQL databases.; Used Docker and Git in team development. |
| CAN_4CFB167D7487 | Skills | 7 -> 8 | Communication | API; API Testing |
| CAN_4CFB167D7487 | Certifications | 3 -> 3 | Python / Domain Certification | Python Domain Certification |
| CAN_4CFB167D7487 | Education | 1 -> 1 | Degree: Bachelor of Technology; Field: Computer Science and Engineering; Institution: KTU; Year: 2026 | Degree: Bachelor of Technology; Field: Computer Science and Engineering; University: KTU; Year: 2026 |
| CAN_4CFB167D7487 | Experience | 2 -> 2 | Python Developer; Tech Nova Labs; Jan 2026 to Apr 2026; 4 months; Built REST API endpoints using Fast API and validated request payloads.; Worked with PostgreSQL queries, Git branches and API testing.; Backend Trainee; Code Nest Academy; Jun 2025 to Dec 202... | Python Developer; TechNova Labs; Jan 2026 to Apr 2026; 4 months; Built REST API endpoints using FastAPI and validated request payloads.; Worked with PostgreSQL queries, Git branches and API testing.; Backend Trainee; CodeNest Academy; Jun 2025 to Dec 2025; ... |
| CAN_5441F5865D9B | Skills | 2 -> 4 | - | Spring; Spring Boot |
| CAN_5441F5865D9B | Certifications | 3 -> 3 | Java / Domain Certification | Java Domain Certification |
| CAN_5441F5865D9B | Education | 1 -> 1 | Degree: Bachelor of Technology; Field: Electronics and Communication Engineering; Year: 2025 | Degree: Bachelor of Technology; Field: Electronics and Communication Engineering; University: KTU; Year: 2025 |
| CAN_5441F5865D9B | Experience | 1 -> 1 | Software Trainee; App Works Academy; Jan 2026 to May 2026; 5 months; Developed basic Java applications.; Practiced Spring Boot concepts and SQL queries. | Software Trainee; AppWorks Academy; Jan 2026 to May 2026; 5 months; Developed basic Java applications.; Practiced Spring Boot concepts and SQL queries. |
| CAN_572F92BAB63C | Skills | 10 -> 11 | - | Payroll |
| CAN_572F92BAB63C | Experience | 1 -> 1 | HR Executive Intern; Talent Bridge Solutions; Jan 2026 to Jun 2026; 6 months; Coordinated candidate interview schedules, screened applicant profiles, and assisted in talent acquisition.; Maintained accurate employee records, updated HRMS databases, and supp... | HR Executive Intern; TalentBridge Solutions; Jan 2026 to Jun 2026; 6 months; Coordinated candidate interview schedules, screened applicant profiles, and assisted in talent acquisition.; Maintained accurate employee records, updated HRMS databases, and suppo... |
| CAN_5DB428DE94C1 | Experience | 1 -> 1 | HR Assistant Trainee; Talent Bridge Academy; Aug 2025 to Mar 2026; 8 months; Assisted with candidate screening and interview scheduling.; Maintained basic employee records.; Prepared Excel reports and office documents. | HR Assistant Trainee; TalentBridge Academy; Aug 2025 to Mar 2026; 8 months; Assisted with candidate screening and interview scheduling.; Maintained basic employee records.; Prepared Excel reports and office documents. |
| CAN_79F428525AFE | Skills | 12 -> 11 | Applicant Tracking System (baseline-only false positive: 'ATS' appears in the PDF header, not in the candidate's Skills section) | - |
| CAN_79F428525AFE | Experience | 2 -> 2 | Tamil Nadu; Jan 2021 to Present; 69 months; Coordinated recruitment and interview scheduling.; Supported onboarding and employee records.; Prepared HR reports using Excel.; HR Assistant; Office People; 2019 to 2020; 13 months; Maintained employee documentat... | HR Executive; TalentBridge Solutions; Jan 2021 to Present; 70 months; Coordinated recruitment and interview scheduling.; Supported onboarding and employee records.; Prepared HR reports using Excel.; HR Assistant; OfficePeople; 2019 to 2020; 13 months; Maint... |
| CAN_7B72257C5D85 | Certifications | 3 -> 3 | HR Operations / Domain Certification | HR Operations Domain Certification |
| CAN_7B72257C5D85 | Education | 0 -> 1 | - | Degree: Bachelor of Business Administration; Field: Human Resources; Year: 2026 |
| CAN_7B72257C5D85 | Experience | 1 -> 1 | HR Intern; People First Services; Jan 2026 to Jun 2026; 6 months; Supported recruitment screening and interview scheduling.; Maintained employee records and HR documentation.; Used MS Excel for basic HR reports. | HR Intern; PeopleFirst Services; Jan 2026 to Jun 2026; 6 months; Supported recruitment screening and interview scheduling.; Maintained employee records and HR documentation.; Used MS Excel for basic HR reports. |
| CAN_81791789C6AA | Skills | 8 -> 8 | Communication | API |
| CAN_81791789C6AA | Certifications | 3 -> 3 | Python / Domain Certification | Python Domain Certification |
| CAN_81791789C6AA | Education | 1 -> 1 | Degree: Bachelor of Technology; Field: Computer Science and Engineering; Year: 2020 | Degree: Bachelor of Technology; Field: Computer Science and Engineering; University: VTU; Year: 2020 |
| CAN_81791789C6AA | Experience | 2 -> 2 | Python Developer; Soft Labs; Jan 2022 to Present; 57 months; Designed backend services and REST APIs for enterprise applications.; Worked with PostgreSQL, Docker and AWS environments.; Python Developer; Web Core; Jun 2020 to Dec 2021; 19 months; Built Djang... | Python Developer; SoftLabs; Jan 2022 to Present; 58 months; Designed backend services and REST APIs for enterprise applications.; Worked with PostgreSQL, Docker and AWS environments.; Python Developer; WebCore; Jun 2020 to Dec 2021; 19 months; Built Django ... |
| CAN_B67DE2B9BADB | Skills | 3 -> 8 | Communication | Object-Oriented Programming; MySQL; JavaScript; HTML; CSS; Git |
| CAN_B67DE2B9BADB | Education | 1 -> 1 | Degree: Bachelor of Technology; Field: Electronics Communication Engineering 2026; Institution: KTU; Year: 2026 | Degree: Bachelor of Technology; Field: Electronics and Communication Engineering; University: KTU; Year: 2026 |
| CAN_B67DE2B9BADB | Experience | 1 -> 1 | Software Trainee; Learn Code Institute; Aug 2025 to Mar 2026; 8 months; Prepared SQL queries and documented application workflows. | Software Trainee; LearnCode Institute; Aug 2025 to Mar 2026; 8 months; Prepared SQL queries and documented application workflows. |
| CAN_C5D1338F49C1 | Skills | 10 -> 10 | Communication | API |
| CAN_C5D1338F49C1 | Certifications | 3 -> 3 | Python / Domain Certification | Python Domain Certification |
| CAN_C5D1338F49C1 | Education | 1 -> 1 | Degree: Bachelor of Technology; Field: Computer Science and Engineering; Year: 2020 | Degree: Bachelor of Technology; Field: Computer Science and Engineering; University: KTU; Year: 2020 |
| CAN_C5D1338F49C1 | Experience | 2 -> 2 | Python Developer; Cloud Axis Technologies; Jan 2022 to Present; 57 months; Designed REST APIs using Fast API and Django.; Built PostgreSQL data models and optimized queries.; Managed Git workflows and production releases.; Python Developer; Web Core Systems... | Python Developer; CloudAxis Technologies; Jan 2022 to Present; 58 months; Designed REST APIs using FastAPI and Django.; Built PostgreSQL data models and optimized queries.; Managed Git workflows and production releases.; Python Developer; WebCore Systems; J... |
| CAN_CB63A04EDA0B | Skills | 9 -> 11 | SQL | API; Git; Applicant Tracking System |
| CAN_CB63A04EDA0B | Education | 1 -> 1 | Degree: Bachelor of Technology; Field: Computer Science and Engineering; Year: 2019 | Degree: Bachelor of Technology; Field: Computer Science and Engineering; University: VTU; Year: 2019 |
| CAN_CB63A04EDA0B | Experience | 3 -> 3 | Python Developer; Cloud Bridge Systems; Apr 2022 to Present; 54 months; Designed Fast API micro services and Postgre SQL-backed workflows.; Introduced Redis caching and improved high-volume API response times.; Python Developer; Data Works Pvt Ltd; Jun 2020... | Python Developer; CloudBridge Systems; Apr 2022 to Present; 55 months; Designed FastAPI microservices and PostgreSQL-backed workflows.; Introduced Redis caching and improved high-volume API response times.; Python Developer; DataWorks Pvt Ltd; Jun 2020 to M... |
| CAN_E3036E1C2BDA | Skills | 13 -> 12 | Angular (baseline-only false positive: a one-character source 'l' was fuzzy-matched to Angular; the resume contains no Angular evidence) | - |
| CAN_E3036E1C2BDA | Experience | 3 -> 3 | People Sphere Bengaluru; Apr 2021 to Present; 66 months; People Sphere Bengaluru, Karnataka; Managed end to end recruitment, interview coordination and onboarding.; Maintained HR metrics and supported employee relations activities.; Talent Works Bengaluru; ... | Senior HR Executive; PeopleSphere; Apr 2021 to Present; 67 months; Senior HR Executive; PeopleSphere; Managed end-to-end recruitment, interview coordination and onboarding.; Maintained HR metrics and supported employee relations activities.; HR Executive; T... |

## ATS score changes

| Candidate | Job | Old score | Optimized score | Change | Weights changed? |
|---|---|---:|---:|---:|---|
| CAN_2325AD0B18CE | JOB_0E2E9FA9C79D | 84.69 | 84.42 | -0.27 | No |
| CAN_79F428525AFE | JOB_0E2E9FA9C79D | 64.81 | 67.27 | +2.46 | No |
| CAN_E3036E1C2BDA | JOB_0E2E9FA9C79D | 61.61 | 75.19 | +13.58 | No |
| CAN_410B14422E90 | JOB_57C5EC85A717 | 56.00 | 60.94 | +4.94 | No |
| CAN_81791789C6AA | JOB_57C5EC85A717 | 80.15 | 76.82 | -3.33 | No |
| CAN_C5D1338F49C1 | JOB_57C5EC85A717 | 93.00 | 87.62 | -5.38 | No |
| CAN_CB63A04EDA0B | JOB_57C5EC85A717 | 80.40 | 81.97 | +1.57 | No |
| CAN_1CA3DA4F0062 | JOB_6EC0B8C25121 | 64.40 | 62.98 | -1.42 | Yes |
| CAN_572F92BAB63C | JOB_6EC0B8C25121 | 78.90 | 84.30 | +5.40 | Yes |
| CAN_5DB428DE94C1 | JOB_6EC0B8C25121 | 60.04 | 58.23 | -1.81 | Yes |
| CAN_7B72257C5D85 | JOB_6EC0B8C25121 | 49.44 | 67.61 | +18.17 | Yes |
| CAN_4CFB167D7487 | JOB_BF2FEFE4A4A3 | 87.04 | 95.16 | +8.12 | No |
| CAN_5441F5865D9B | JOB_BF2FEFE4A4A3 | 28.81 | 37.30 | +8.49 | No |
| CAN_B67DE2B9BADB | JOB_BF2FEFE4A4A3 | 37.77 | 52.06 | +14.29 | No |
| CAN_CB63A04EDA0B | JOB_BF2FEFE4A4A3 | 78.55 | 88.23 | +9.68 | No |

The CSV includes complete old and optimized extracted values for each section. Score rows include the four component scores and note whether score weights changed. Enable text wrapping in Excel to read multi-value cells. The raw JSON-path diff remains in `comparison_table.csv`.
