# ITB Admission Website URLs for Crawling

This file contains all URLs extracted from `Informasi Umum ITB - Tabel.xlsx` with their status and reference information.

Generated: 2026-01-25

---

## Summary
- Total unique URLs: 11
- Accessible URLs: 10
- URLs with issues: 1 (typo)

---

## URL List

### 1. International Master Program
**URL**: `https://admission.itb.ac.id/info/international-master-program/`
**Status**: ✅ Accessible (200 OK)
**Referenced by sheets**:
- Program Studi Magister dan Pasc
- International Magister and Doct
- Magister and Doctoral Registrat

---

### 2. Student Exchange Program
**URL**: `https://admission.itb.ac.id/exchange/#home`
**Status**: ✅ Accessible (200 OK)
**Referenced by sheets**:
- ITB Student Exchange Schedule
- Student Exchange Tuition Fee

---

### 3. Program Keinsinyuran
**URL**: `https://admission.itb.ac.id/info/keinsiyuran/`
**Status**: ⚠️ **404 Not Found (TYPO)**
**Correct URL**: `https://admission.itb.ac.id/info/keinsinyuran/` (accessible)
**Issue**: Missing 'n' in "keinsiyuran" → should be "keinsinyuran"
**Referenced by sheets**:
- Jadwal Keinsinyuran
- Program Studi Program Keinsinyu

---

### 4. Program Profesi Apoteker
**URL**: `https://admission.itb.ac.id/info/apoteker/`
**Status**: ✅ Accessible (200 OK)
**Referenced by sheets**:
- Jadwal Pendaftaran Program Prof

---

### 5. Program Non-Reguler Non-Gelar
**URL**: `https://admission.itb.ac.id/info/nrng/`
**Status**: ✅ Accessible (200 OK)
**Referenced by sheets**:
- Jadwal Pelaksanaan Program Non

---

### 6. Program MBKM ITB-UNP
**URL**: `https://admission.itb.ac.id/info/mbkm/`
**Status**: ✅ Accessible (200 OK)
**Referenced by sheets**:
- Jadwal Pelaksanaan MBKM ITB-UNP

---

### 7. Summer Course Programs
**URL**: `https://admission.itb.ac.id/info/summer-courses-non-regular/`
**Status**: ✅ Accessible (200 OK)
**Referenced by sheets**:
- ITB Summer Course Programs
- ITB Virtual Course Tuition Fee

---

### 8. International Scholarship Program
**URL**: `https://admission.itb.ac.id/info/international-scholarship/`
**Status**: ✅ Accessible (200 OK)
**Referenced by sheets**:
- Program Beasiswa

---

### 9. Program Magister
**URL**: `https://admission.itb.ac.id/info/program-magister/`
**Status**: ✅ Accessible (200 OK)
**Referenced by sheets**:
- Jadwal Pendaftaran Magister S2

---

### 10. Program Sarjana (S1)
**URL**: `https://admission.itb.ac.id/info/info-pendaftaran-program-sarjana/`
**Status**: ✅ Accessible (200 OK)
**Referenced by sheets**:
- Jadwal Kegiatan SNBP
- Jadwal Kegiatan SNBT
- Jadwal Kegiatan SM ITB
- Program Studi S1
- Biaya Pendidikan S1 SNBT dan SN
- Daya Tampung SNBP Peminatan
- Daya Tampung S1 ITB

---

### 11. International Undergraduate Program (IUP)
**URL**: `https://admission.itb.ac.id/info/international-undergraduate-program/`
**Status**: ✅ Accessible (200 OK)
**Referenced by sheets**:
- ITB IUP Program Sched
- IUP Fee Component

---

## Quick Reference for Crawling

### All Accessible URLs
```bash
https://admission.itb.ac.id/info/international-master-program/
https://admission.itb.ac.id/exchange/#home
https://admission.itb.ac.id/info/keinsinyuran/  # Use this corrected URL
https://admission.itb.ac.id/info/apoteker/
https://admission.itb.ac.id/info/nrng/
https://admission.itb.ac.id/info/mbkm/
https://admission.itb.ac.id/info/summer-courses-non-regular/
https://admission.itb.ac.id/info/international-scholarship/
https://admission.itb.ac.id/info/program-magister/
https://admission.itb.ac.id/info/info-pendaftaran-program-sarjana/
https://admission.itb.ac.id/info/international-undergraduate-program/
```

### JSON Format for Automation
```json
{
  "urls": [
    {
      "url": "https://admission.itb.ac.id/info/international-master-program/",
      "status": "accessible",
      "description": "International Master Program",
      "source_sheets": ["Program Studi Magister dan Pasc", "International Magister and Doct", "Magister and Doctoral Registrat"]
    },
    {
      "url": "https://admission.itb.ac.id/exchange/#home",
      "status": "accessible",
      "description": "Student Exchange Program",
      "source_sheets": ["ITB Student Exchange Schedule", "Student Exchange Tuition Fee"]
    },
    {
      "url": "https://admission.itb.ac.id/info/keinsinyuran/",
      "status": "accessible",
      "note": "Corrected from typo 'keinsiyuran'",
      "description": "Program Keinsinyuran",
      "source_sheets": ["Jadwal Keinsinyuran", "Program Studi Program Keinsinyu"]
    },
    {
      "url": "https://admission.itb.ac.id/info/apoteker/",
      "status": "accessible",
      "description": "Program Profesi Apoteker",
      "source_sheets": ["Jadwal Pendaftaran Program Prof"]
    },
    {
      "url": "https://admission.itb.ac.id/info/nrng/",
      "status": "accessible",
      "description": "Program Non-Reguler Non-Gelar",
      "source_sheets": ["Jadwal Pelaksanaan Program Non"]
    },
    {
      "url": "https://admission.itb.ac.id/info/mbkm/",
      "status": "accessible",
      "description": "Program MBKM ITB-UNP",
      "source_sheets": ["Jadwal Pelaksanaan MBKM ITB-UNP"]
    },
    {
      "url": "https://admission.itb.ac.id/info/summer-courses-non-regular/",
      "status": "accessible",
      "description": "Summer Course Programs",
      "source_sheets": ["ITB Summer Course Programs", "ITB Virtual Course Tuition Fee"]
    },
    {
      "url": "https://admission.itb.ac.id/info/international-scholarship/",
      "status": "accessible",
      "description": "International Scholarship Program",
      "source_sheets": ["Program Beasiswa"]
    },
    {
      "url": "https://admission.itb.ac.id/info/program-magister/",
      "status": "accessible",
      "description": "Program Magister",
      "source_sheets": ["Jadwal Pendaftaran Magister S2"]
    },
    {
      "url": "https://admission.itb.ac.id/info/info-pendaftaran-program-sarjana/",
      "status": "accessible",
      "description": "Program Sarjana (S1)",
      "source_sheets": ["Jadwal Kegiatan SNBP", "Jadwal Kegiatan SNBT", "Jadwal Kegiatan SM ITB", "Program Studi S1", "Biaya Pendidikan S1 SNBT dan SN", "Daya Tampung SNBP Peminatan", "Daya Tampung S1 ITB"]
    },
    {
      "url": "https://admission.itb.ac.id/info/international-undergraduate-program/",
      "status": "accessible",
      "description": "International Undergraduate Program (IUP)",
      "source_sheets": ["ITB IUP Program Sched", "IUP Fee Component"]
    }
  ]
}
```

---

## Notes

1. **Base Domain**: All URLs are under `admission.itb.ac.id`
2. **Content Type**: These are ITB admission/informational pages
3. **Crawling Recommendations**:
   - Use appropriate request intervals to avoid overwhelming the server
   - Monitor for rate limiting (consider using `robots.txt` to check crawling policies)
   - Some URLs contain hash fragments (`#home`) - these may need special handling
   - The corrected URL for Program Keinsinyuran should be used instead of the typo version
4. **Data Structure**: Each page likely contains:
   - Schedule information (jadwal)
   - Program details (program studi)
   - Fee information (biaya pendidikan)
   - Requirements and eligibility

---

## Maintenance

- Last checked: 2026-01-25
- Re-verify URLs periodically as admission pages may change
- Update this file when new URLs are added to the source XLSX
