# TODO for User – Data Gaps and Placeholders

## Items Requiring User Input or Verification

### Priority 1 – Sales Data Verification
- [ ] **Q3 2023 Lumakras sales**: Web search did not return an explicit figure for Q3 2023.
  I derived $52M (FY2023 ≈ $295M minus Q1 $74M + Q2 $77M + Q4 $92M = $243M → Q3 = $52M).
  **Action**: Verify against Amgen Q3 2023 10-Q filing on SEC EDGAR.

- [ ] **FY2021 sales reconciliation**: Some sources report $90M, others ~$117M (possibly including ex-US).
  Current model uses US-only: Q2=$36M + Q3=$36M + Q4=$45M = $117M or Q2=$9M + Q3=$36M + Q4=$45M = $90M.
  **Action**: Confirm from Amgen 2021 10-K whether $90M is US-only or global.

### Priority 2 – Analog Launch Sales
- [ ] **Quarterly sales trajectories for 8-12 analog launches**: I need Q-by-Q sales (indexed to launch quarter) for:
  1. Tagrisso (osimertinib) – AstraZeneca, EGFR T790M NSCLC, approved Nov 2015
  2. Xalkori (crizotinib) – Pfizer, ALK+ NSCLC, approved Aug 2011
  3. Alecensa (alectinib) – Roche, ALK+ NSCLC, approved Dec 2015
  4. Lorbrena (lorlatinib) – Pfizer, ALK+ NSCLC, approved Nov 2018
  5. Tabrecta (capmatinib) – Novartis, MET ex14 NSCLC, approved May 2020
  6. Tepmetko (tepotinib) – EMD Serono, MET ex14 NSCLC, approved Feb 2021
  7. Vitrakvi (larotrectinib) – Bayer, NTRK fusion, approved Nov 2018
  8. Rozlytrek (entrectinib) – Roche, NTRK/ROS1, approved Aug 2019
  9. Retevmo (selpercatinib) – Lilly, RET, approved May 2020
  10. Gavreto (pralsetinib) – Blueprint/Roche, RET, approved Sep 2020

  **Action**: These can be pulled from company 10-K/10-Q filings. I will populate what I can from web searches; user should verify or provide corrections.

### Priority 3 – Epidemiology Cross-checks
- [ ] **SEER stage distribution**: The 70% advanced/metastatic fraction is a standard literature estimate.
  **Action**: If you have SEER*Stat access, pull exact Stage III+IV fraction for lung adenocarcinoma 2018-2020.

- [ ] **Biomarker testing rate at launch (50%)**: This is the most uncertain input. Community oncology
  testing rates for KRAS specifically (not just EGFR/ALK) were probably 30-50% in mid-2021.
  **Action**: If you have access to Guardant or Foundation Medicine testing rate reports, update this.

### Priority 4 – CMS Part D Cross-check
- [ ] **CMS Part D spending data for Lumakras**: Available from CMS Medicare Part D Spending dashboard.
  **Action**: Download from https://data.cms.gov/summary-statistics-on-use-and-payments/medicare-medicaid-opioid-prescribing-rates/medicare-part-d-spending-by-drug
  This serves as a cross-check on the commercial sales figures.

### Priority 5 – Competitor Pipeline (for AACT/ClinicalTrials.gov)
- [ ] **AACT database access**: The project uses ClinicalTrials.gov API for competitor pipeline data.
  If you have access to the AACT PostgreSQL dump, we can run richer queries.
  **Action**: Confirm if AACT DB access is available or if API-only is acceptable.

---
*Last updated: 2026-09-29*
