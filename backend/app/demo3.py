"""Demo project DEMO-03: case study from SRA/MOC/OPS/001/IX/2026 Rev 00 —
"Assessment Operasi 24 Jam Aerodrome Alternate" (Gunung Anak Krakatau eruption, closure of WIII).

Content is transcribed from the SRA report (Indonesian, as in the source). Hazard ratings use the report's
"Current" column as the initial/current rating and the "Residual" column as residual; the "Inherent" rating
is kept in the hazard context. Probabilities are conditional on the active contingency (assumption A-01).
"""
from datetime import date

from sqlalchemy.orm import Session

from .engines import fta as fta_engine
from .models import Action, Assessment, Control, Hazard, Project, Study

DOC = "SRA/MOC/OPS/001/IX/2026 Rev 00"
AERODROMES = "WAHI · WAHH · WAHQ · WAHS · WICA · WICC · WIPP"
REVIEW = date(2026, 10, 20)  # H+30 after issue on 20 Sep 2026

GROUPS = {"G": "G — Kelayakan fisik aerodrome", "C": "C — Kapasitas dan arus lalu lintas", "H": "H — Faktor manusia",
          "T": "T — Teknis dan fasilitas", "E": "E — Lingkungan (abu vulkanik)", "O": "O — Organisasi dan koordinasi",
          "S": "S — Layanan pendukung"}

# register rows use the HAZID prompt list so guideword coverage works; the SRA group is kept in the hazard's system field
HAZID_GW = {"G": "Airspace and aerodrome", "C": "Traffic", "H": "People", "T": "Equipment / systems", "E": "Environment",
            "O": "Organisation", "S": "Interfaces"}

# id, hazard, worst credible consequence, inherent, existing barrier & condition, barrier quality, current, mitigations, residual, justification
HAZARDS = [
    ("G-01", "Kategori ARFF terpasang lebih rendah dari kategori armada yang akan dilayani (seluruh alternate)",
     "Kecelakaan widebody tanpa kapasitas penyelamatan memadai → korban jiwa yang tidak dapat dicegah", "5A",
     "Tidak ada. Dokumen lama tidak mengidentifikasi hazard ini", None, "5A", ["M-03"], "2A",
     "Probabilitas turun dari Frequent ke Improbable karena kondisinya dihilangkan: tipe pesawat dibatasi agar sesuai kategori terpasang, atau kategori dinaikkan. Severity tetap A — mitigasi tidak mengubah akibat kecelakaan, hanya peluang terjadinya ketidaksesuaian."),
    ("G-02", "WICC ditetapkan sebagai alternate WIII meski runway 2.220 m dan tidak mampu widebody",
     "Pesawat widebody terlanjur diversion ke aerodrome yang tidak dapat menerimanya", "5A",
     "Tidak ada; dokumen lama justru menilai beban widebody di WICC sebagai 2D", None, "5A", ["M-01"], "2D",
     "Hazard dieliminasi: WICC tidak lagi dipublikasikan sebagai alternate widebody. Sisa risiko adalah kesalahan flight planning operator terhadap batas yang sudah dipublikasikan."),
    ("G-03", "PCN WAHS (61) dan WAHQ (68) di bawah ACN widebody pada bobot pendaratan tinggi",
     "Kerusakan perkerasan; runway tidak dapat dipakai justru saat paling dibutuhkan", "4C",
     "Tidak ada pembatasan bobot yang dipublikasikan", None, "4C", ["M-01", "M-03"], "2C",
     "Pembatasan bobot pendaratan dipublikasikan; penerimaan widebody di WAHS dan WAHQ dihentikan."),
    ("G-04", "Prosedur instrumen dan minima operasi malam belum diverifikasi pada unit yang selama ini tidak beroperasi H24",
     "Missed approach berulang; pengalihan lanjutan dengan bahan bakar terbatas", "4B",
     "Prosedur dipublikasikan di AIP — kondisi: belum diuji pada kondisi malam + menghindari sebaran abu", "poor", "3B", ["M-11"], "3C",
     "Severity turun satu kelas karena operational trial (PK-8) memverifikasi minima dan menambahkan barrier pemulih (alternate kedua dijamin). Probabilitas tidak diklaim turun."),
    ("G-05", "Airfield lighting, PAPI, dan marka belum diverifikasi untuk operasi malam berkelanjutan",
     "Pendaratan malam tidak dapat dilayani; diversion menunggu hingga pagi", "4C",
     "Sertifikasi bandar udara & inspeksi berkala operator — kondisi: tidak diverifikasi untuk H24", "poor", "3C", ["M-15"], "2C",
     "Verifikasi bersama operator bandara sebelum status H24 dipublikasikan; keterbatasan yang tersisa dipublikasikan melalui NOTAM."),
    ("C-01", "Margin kapasitas jaringan hanya 4% pada alokasi kapasitas penuh, tanpa daur ulang stand dalam S1",
     "Pesawat menunggu di taxiway/runway; konflik di manuvering area → runway incursion", "5B",
     "Koordinasi ad hoc dengan operator bandara — kondisi: lemah, tanpa angka", "very poor", "4B", ["M-04", "M-05", "M-10"], "3C",
     "Probabilitas turun satu level karena hard cap ditegakkan sistem; severity turun satu kelas karena remote parking memberi barrier pemulih terhadap penumpukan di manuvering area."),
    ("C-02", "Tidak ada hard cap penerimaan yang dapat ditegakkan; keputusan menerima diambil per kejadian",
     "Aerodrome menerima melampaui kapasitas; pesawat berikutnya tidak punya opsi", "5B",
     "Tidak ada. ATFM belum memiliki parameter batas per aerodrome", None, "4B", ["M-04"], "2C",
     "Penurunan dua level probabilitas dijustifikasi: batas tidak lagi bergantung pada keputusan manusia per kejadian melainkan ditegakkan sebagai parameter sistem — perubahan sistemik, bukan pengawasan."),
    ("C-03", "Defisit posisi saat sebagian alternate ikut terdampak abu — hingga 11 widebody dan 23 narrow-body pada pola terburuk",
     "Widebody tanpa alternate berkemampuan dalam jangkauan bahan bakar → fuel exhaustion", "5A",
     "Tidak ada alternate cadangan di luar sektor abu yang ditetapkan", None, "4A", ["M-02", "M-09"], "2B",
     "Alternate tambahan di luar kedua sektor sebaran abu menutup defisit pola terburuk — 11 posisi Code-E dan 23 Code-C — sehingga alokasi kapasitas penuh kembali surplus pada seluruh pola angin yang diuji. Severity turun satu kelas karena kebijakan extra fuel memberi margin pemulihan menuju alternate berikutnya."),
    ("C-04", "Lonjakan beban kerja ATC dari <1 menjadi ±6 pergerakan/jam pada unit berpengalaman rendah (WICA: 0,13 → 6/jam)",
     "Kesalahan clearance; loss of separation", "4B",
     "Rating dan ujian personel (baseline, bukan mitigasi); pre-shift briefing", "poor", "4B", ["M-04", "M-06", "M-17"], "3C",
     "Hard cap membatasi laju kedatangan pada tingkat yang diuji; dua personel per posisi memberi verifikasi silang; simulasi surge menaikkan kesiapan."),
    ("C-05", "Kapasitas holding dan struktur ruang udara di sekitar alternate tidak dinilai untuk beban kontingensi",
     "Penumpukan di udara; excessive delay pada pesawat berbahan bakar terbatas", "4B",
     "Prosedur ATS yang berlaku; koordinasi dengan ACC", "good", "3B", ["M-04"], "2C",
     "Pengaturan flow mencegah penumpukan di udara; kebutuhan holding berkurang seiring batas penerimaan yang jelas."),
    ("C-06", "Lalu lintas reguler alternate tetap berjalan bersamaan dengan gelombang diversion",
     "Konflik jadwal; stand terpakai oleh operasi rutin saat dibutuhkan", "4D",
     "Tidak ada prosedur prioritas yang ditetapkan", None, "4D", ["M-04", "M-16"], "2D",
     "Prosedur prioritas dan alokasi stand ditetapkan sebelum aktivasi."),
    ("H-01", "Pola dinas H24 baru dengan shift malam yang belum pernah dijalankan unit",
     "Fatigue-induced error → loss of separation", "4B",
     "Ketentuan jam kerja & istirahat; pengawasan supervisor; pemeriksaan fitness for duty — kondisi: memadai tetapi tidak tervalidasi untuk pola baru", "poor", "4B", ["M-06", "M-12"], "3C",
     "Probabilitas turun satu level berdasarkan roster yang tervalidasi model, bukan berdasarkan pengawasan. Severity turun satu kelas karena dua personel per posisi memberi pemulihan terhadap kesalahan individu."),
    ("H-02", "Single-manning pada shift malam tanpa relief dan tanpa cross-check",
     "Inkapasitasi tanpa deteksi; kesalahan tanpa verifikasi silang → loss of separation", "4B",
     "Tidak ada. Pada dokumen sebelumnya justru dicantumkan sebagai kontrol", None, "4B", ["M-06"], "2C",
     "Penurunan dua level dijustifikasi: single-manning dilarang, dan perhitungan kecukupan roster (Bab 4.2.5) menunjukkan larangan ini dapat dipenuhi tanpa tambahan personel di Semarang. Sisa risiko adalah pelanggaran larangan."),
    ("H-03", "Penurunan currency pada unit bertraffic sangat rendah (WICA 3,0/hari, WICC 9,4/hari)",
     "Respons lambat pada beban tinggi; kesalahan prosedural", "4C",
     "Program proficiency check reguler — kondisi: tidak mencakup skenario beban tinggi", "poor", "3C", ["M-17"], "2D",
     "Refresher dan simulasi beban tinggi memulihkan currency sebelum aktivasi."),
    ("H-04", "Transisi mendadak dari low traffic ke surge pada dini hari",
     "Hilangnya situational awareness; attention tunneling", "4C",
     "Pre-shift briefing; handover checklist — kondisi: sedang", "poor", "3C", ["M-11", "M-17"], "2D",
     "Butir khusus surge pada handover checklist; simulasi transisi dini hari."),
    ("H-05", "Pengalaman menangani widebody dan kru asing terbatas pada unit yang bersangkutan",
     "Kesalahan komunikasi; salah pemahaman instruksi", "3C",
     "Kompetensi bahasa Inggris tersertifikasi (baseline)", "good", "3C", ["M-17"], "2D",
     "Familiarisation penanganan widebody dan frasa standar untuk kru asing."),
    ("H-06", "Akses transportasi personel ke tower pada dini hari (WAHI dan WICA jauh dari kota)",
     "Personel tidak tiba; posisi tidak terisi; unit tidak dapat dibuka", "4C",
     "Tidak ada pengaturan transportasi khusus", None, "4C", ["M-12"], "2D",
     "Pengaturan transportasi dan akomodasi personel dini hari ditetapkan dan dibiayai."),
    ("T-01", "Catu daya belum diuji beban penuh untuk operasi kontinu; genset tunggal di sebagian lokasi",
     "Padamnya seluruh fasilitas ATS → hilangnya pelayanan mendadak", "4B",
     "PLN + UPS + genset; pemeriksaan harian. WIPP: teruji 1 & 6 Sep 2026 (bukti ada). WAHS: belum teruji, genset tunggal", "poor", "3B", ["M-07"], "2C",
     "Didukung perhitungan FTA: P(ATS blackout) selama 30 hari turun dari 4,6×10⁻³ ke 2,9×10⁻⁴. Severity turun karena prosedur degraded mode teruji."),
    ("T-02", "Jendela pemeliharaan preventif hilang pada operasi H24; duty cycle peralatan CNS berubah",
     "Kegagalan peralatan justru pada periode beban tertinggi", "4C",
     "SOP pemeliharaan; redundansi peralatan utama; teknisi standby — kondisi: jadwal belum disesuaikan", "poor", "3C", ["M-18"], "2D",
     "Jadwal pemeliharaan disesuaikan untuk operasi tanpa jendela shutdown; suku cadang kritis di lokasi."),
    ("T-03", "Ketahanan tautan komunikasi (VSAT/terestrial) ke ACC pada operasi kontinu",
     "Hilangnya koordinasi antar-unit; ATS terdegradasi", "3B",
     "Redundansi tautan; prosedur komunikasi cadangan", "good", "2B", ["M-18"], "2D",
     "Redundansi tautan diverifikasi dan prosedur komunikasi cadangan diuji — barrier pemulih nyata."),
    ("T-04", "Kapasitas perekaman suara dan surveilans untuk operasi 24 jam berkelanjutan",
     "Hilangnya data investigasi; ketidakpatuhan regulasi", "4D",
     "Sistem perekaman eksisting — kondisi: kapasitas belum dihitung untuk H24", "poor", "3D", ["M-18"], "2D",
     "Kapasitas perekaman dihitung dan ditambah untuk siklus 24 jam."),
    ("E-01", "Aerodrome alternate berada di dalam polygon sebaran abu yang sama dengan WIII (WICA, WICC per ASHTAM VAWR3751), sehingga ketersediaannya tunduk pada rantai keputusan yang sama",
     "Diversion menuju alternate yang kemudian ditutup; pengalihan kedua dengan bahan bakar menipis → fuel exhaustion", "5A",
     "ASHTAM dan paper-test periodik — kondisi: keduanya alat deteksi, bukan barrier terhadap ketidaktersediaan", "very poor", "5A", ["M-02", "M-08", "M-09"], "2B",
     "Penurunan besar dijustifikasi oleh substitusi: alternate widebody utama dipindahkan ke luar sektor sebaran abu, sehingga korelasi dengan kejadian penutup WIII diputus. Severity turun satu kelas karena extra fuel dan alternate ketiga memberi jalur pemulihan."),
    ("E-02", "Kontaminasi abu pada runway alternate menurunkan friksi, terdeteksi terlambat pada malam hari",
     "Runway excursion saat pendaratan widebody", "4B",
     "Tidak ada prosedur pengukuran friksi dan pelaporan RCR terkait abu pada malam hari", None, "4B", ["M-13"], "3C",
     "Pengukuran friksi dan pelaporan RCR khusus abu membuat kontaminasi terdeteksi sebelum berdampak; kriteria penutupan runway memberi barrier pemulih."),
    ("E-03", "Abu pada antena/radome radar, DVOR, ILS, sensor angin; penyumbatan filter AC ruang peralatan",
     "Degradasi sinyal navigasi dan surveilans secara bertahap tanpa alarm", "4C",
     "Pemeliharaan berkala — kondisi: tidak ada prosedur khusus abu", "poor", "4C", ["M-13", "M-18"], "2C",
     "Prosedur pembersihan khusus abu untuk antena, radome, sensor, dan filter AC ruang peralatan."),
    ("E-04", "Paparan abu pada personel yang bertugas; penurunan ketersediaan personel",
     "Kekurangan personel; penghentian sebagian pelayanan", "3C",
     "APD dan masker; pemeriksaan kesehatan; ruang kerja tertutup (praktik Semarang)", "good", "2C", ["M-15"], "2D",
     "APD, pemeriksaan kesehatan, dan koordinasi fasilitas kesehatan diformalkan dalam SLA."),
    ("E-05", "Paper-test dilaksanakan secara periodik, sehingga terdapat jeda waktu antara datangnya abu dan terdeteksinya",
     "Pendaratan pada runway terkontaminasi yang belum terdeteksi → runway excursion", "4B",
     "Paper-test terjadwal oleh operator bandara — kondisi: interval belum ditetapkan untuk kontingensi", "poor", "4B", ["M-19", "M-13"], "3C",
     "Interval paper-test diperpendek dan dilengkapi laporan kru serta inspeksi terjadwal, sehingga jendela tak-terdeteksi menyempit. Severity turun satu kelas karena pengukuran friksi dan kriteria penutupan runway menjadi barrier pemulih."),
    ("E-06", "Sensitivitas paper-test terbatas terhadap abu berkonsentrasi rendah; hasil negatif belum tentu berarti bebas abu",
     "Bandara dinyatakan tetap terbuka padahal abu tipis hadir → kontaminasi mesin dan fasilitas", "4C",
     "Tidak ada metode deteksi lain yang ditetapkan", None, "4C", ["M-19"], "2C",
     "Penurunan dua level dijustifikasi oleh penambahan metode deteksi yang berbeda sifatnya — bukan pengulangan metode yang sama — sehingga kegagalan deteksi tidak lagi bergantung pada satu jenis uji."),
    ("O-01", "Status ketersediaan alternate tidak memiliki sumber otoritatif tunggal maupun batas kedaluwarsa",
     "Alternate yang tidak siap tetap dipakai dalam flight planning → fuel emergency", "5B",
     "Publikasi NOTAM dan koordinasi antar-unit — kondisi: lemah, tanpa timestamp maupun kedaluwarsa", "very poor", "4B", ["M-08"], "2C",
     "Penurunan dua level dijustifikasi: status kedaluwarsa secara otomatis menjadi “not available” — kegagalan sistem mengarah ke kondisi aman (fail-safe), bukan bergantung pada seseorang mengingat memperbarui."),
    ("O-02", "Keputusan menerima diversion diambil berdasarkan data kesiapan bandara yang dapat berumur beberapa jam (temuan STPA)",
     "Pesawat diarahkan ke aerodrome yang statusnya sudah berubah", "4B",
     "Koordinasi lisan supervisor — kondisi: lemah", "very poor", "3B", ["M-08"], "2D",
     "Keputusan penerimaan hanya sah berdasarkan data ber-timestamp dalam TTL."),
    ("O-03", "SOP lokal belum mengatur operasi H24 dan penerimaan diversion massal",
     "Penanganan ad hoc; keputusan tidak seragam antar shift pada beban tertinggi", "4C",
     "SOP unit yang berlaku; ATM Contingency Plan — kondisi: tidak mencakup skenario ini", "poor", "4C", ["M-11"], "2D",
     "SOP H24 terbit, disosialisasikan, dan diuji melalui table-top exercise."),
    ("O-04", "Penambahan titik serah terima pada H24 sementara volume informasi meningkat tajam",
     "Informasi kritis terlewat; keterlambatan penanganan kondisi abnormal", "4C",
     "Checklist handover dalam SOP; operational logbook; fungsi supervisor — kondisi: memadai, perlu butir khusus erupsi", "good", "3C", ["M-11"], "2D",
     "Butir khusus erupsi, durasi minimum handover, dan verifikasi supervisor pada tiap pergantian."),
    ("O-05", "Dukungan lintas fungsi di luar AirNav (ARFF, Avsec, medis, ground handling, bahan bakar, meteorologi) tidak tersedia H24",
     "Alternate tidak mampu menangani diversion secara aman; respons darurat terlambat", "4B",
     "Personel standby dan on-call; Airport Emergency Plan — kondisi: belum ada kesepakatan H24 tertulis", "poor", "3B", ["M-15"], "2C",
     "Kesepakatan H24 tertulis dengan seluruh unit pendukung, disertai readiness confirmation sebelum publikasi status."),
    ("O-06", "JATSC/INMC sebagai simpul koordinasi tunggal berada di dalam area terdampak yang sama",
     "Hilangnya koordinasi jaringan pada saat paling dibutuhkan", "3A",
     "ATM Contingency Plan eksisting — kondisi: belum diuji untuk skenario ini", "poor", "3A", ["M-14"], "2B",
     "Simpul koordinasi cadangan ditetapkan dan diuji; severity turun karena kehilangan koordinasi tidak lagi bersifat total."),
    ("O-07", "Kriteria aktivasi dan terminasi status H24 tidak ditetapkan",
     "Aktivasi terlambat atau terlalu dini; status berubah tanpa pemberitahuan", "4C",
     "Tidak ada", None, "4C", ["M-16"], "2D",
     "Kriteria aktivasi dan terminasi ditetapkan tertulis dengan pengambil keputusan dan lead time yang jelas."),
    ("O-08", "Erosi barrier dan normalisasi penyimpangan pada kontingensi panjang (S3) (temuan FRAM)",
     "Kualitas layanan menurun justru saat kejadian belum berakhir", "4C",
     "Penyiagaan jadwal dinas; koordinasi kantor pusat — kondisi: disiapkan untuk jangka pendek saja", "poor", "4C", ["M-12"], "3C",
     "Rotasi personel dan SPI leading mendeteksi erosi barrier. Tidak diklaim turun ke Acceptable karena erosi organisasi pada S3 bersifat tak terhindarkan dan hanya dapat dideteksi, bukan dihilangkan."),
    ("O-09", "Kewenangan menutup dan membuka kembali bandara berada pada KOBU — di luar batas kendali penyelenggara ATS maupun operator bandara (temuan STPA)",
     "Alternate yang direncanakan ditutup setelah pesawat berkomitmen; penyelenggara ATS tidak dapat menjamin ketersediaan dalam flight planning → fuel emergency", "4B",
     "Koordinasi ad hoc dengan KOBU — kondisi: belum ada mekanisme notifikasi formal", "very poor", "4B", ["M-20", "M-08"], "2C",
     "Kewenangan KOBU tidak berubah — yang berubah adalah kecepatan keputusannya sampai ke pengambil keputusan operasional. Penurunan dua level dijustifikasi karena notifikasi masuk jalur formal dengan target latensi, bukan koordinasi ad hoc. Severity turun karena status kedaluwarsa otomatis menjadi not available."),
    ("O-10", "Latensi rantai VAAC → ASHTAM → paper-test → keputusan KOBU → NOTAM melampaui waktu terbang menuju alternate",
     "Pesawat tiba di aerodrome yang statusnya sudah berubah, dengan bahan bakar terbatas", "4B",
     "Publikasi NOTAM — kondisi: tanpa target latensi maupun pengukuran", "very poor", "4B", ["M-20", "M-08", "M-09"], "2C",
     "Latensi rantai diukur dan ditargetkan (SPI-17); kebijakan extra fuel memberi margin waktu bagi pesawat yang sudah berkomitmen — barrier pemulih terhadap sisa latensi yang tidak dapat dihilangkan."),
    ("S-01", "Stok bahan bakar penerbangan dan laju pengisian ulang di alternate disusun untuk volume normal",
     "Pesawat tidak dapat berangkat kembali; menahan stand; pemulihan operasi tertunda", "5C",
     "Koordinasi dengan operator bandara dan maskapai — kondisi: tanpa angka stok", "poor", "4C", ["M-15"], "2C",
     "Angka stok avtur dan laju pengisian ulang didokumentasikan; perjanjian pasokan kontingensi disepakati."),
    ("S-02", "GSE berkode E (tangga tinggi, GPU besar, pushback tug) tidak tersedia di alternate berperalatan Code C",
     "Pesawat tidak dapat dilayani di darat; stand terkunci", "4D",
     "Tidak ada inventarisasi GSE per aerodrome", None, "4D", ["M-15"], "2D",
     "Inventaris GSE per aerodrome dibuat; alokasi tipe pesawat disesuaikan dengan peralatan tersedia."),
    ("S-03", "Avsec, imigrasi, dan bea cukai untuk penumpang internasional yang dialihkan pada malam hari",
     "Penumpang tertahan tanpa penanganan; gangguan keamanan sisi udara", "4D",
     "Prosedur eksisting jam kerja normal", "good", "3D", ["M-15"], "2D",
     "Prosedur Avsec, imigrasi, dan bea cukai malam hari disepakati dalam SLA."),
]

# id: (text, hierarchy, barrier side, ARAP control kind, owner, prakondisi, verification of closure, SPI)
MITIGATIONS = {
    "M-01": ("Cabut WICC dan WAHH dari daftar alternate widebody; publikasikan batas Code C secara eksplisit di AIP/NOTAM", "Eliminasi", "prevention", "organisational", "Dir. Operasi", "PK-2", "NOTAM/AIP SUP terbit; konfirmasi diterima operator penerbangan", "SPI-01"),
    "M-02": ("Tetapkan alternate tambahan di luar kedua sektor sebaran abu (kandidat WARR, WADD, WAAA, WIBB) yang menyediakan sekurang-kurangnya 11 posisi Code-E dan 23 posisi Code-C, dengan konfirmasi kesiapan tertulis", "Substitusi", "prevention", "organisational", "Direksi", "PK-3", "Kesepakatan tertulis; readiness confirmation per aerodrome; pemodelan dispersi dua pola angin", "SPI-03"),
    "M-03": ("Tutup kesenjangan ARFF: peningkatan ke Kategori 9 melalui mobilisasi kendaraan dan personel, atau pembatasan tipe sesuai kategori terpasang", "Rekayasa / Pembatasan", "prevention", "human-hardware", "Dir. Operasi & Operator Bandara", "PK-1", "Keputusan tertulis DKUPPU; berita acara kesiapan ARFF per lokasi", "SPI-01"),
    "M-04": ("Hitung dan tetapkan hard cap penerimaan per aerodrome per kelas; muat sebagai parameter penegak di sistem ATFM INMC", "Rekayasa", "prevention", "software", "INMC & Dir. Operasi", "PK-4", "Dokumen perhitungan; bukti konfigurasi sistem; hasil uji fungsi", "SPI-02, SPI-03, SPI-04"),
    "M-05": ("Prosedur stop-accept otomatis saat okupansi stand mencapai 80% kapasitas tersedia", "Rekayasa", "prevention", "software", "INMC & Kepala Unit", "PK-4, PK-8", "SOP terbit; ambang terkonfigurasi; diuji pada operational trial", "SPI-02"),
    "M-06": ("FRMS: roster tervalidasi model biomatematis; larangan single-manning pada posisi aktif; batas maksimum perpanjangan dinas yang tidak boleh dilampaui", "Administratif kuat", "prevention", "organisational", "Human Capital & Dir. Operasi", "PK-5", "Laporan pemodelan; roster tertandatangani; rekap kepatuhan bulanan", "SPI-05, SPI-06, SPI-07, SPI-08"),
    "M-07": ("Uji beban penuh PLN–UPS–genset pra-publikasi; genset kedua atau perjanjian genset mobile siaga; stok BBM minimal 7 hari", "Rekayasa", "prevention", "hardware", "Dir. Teknik", "PK-6", "Berita acara uji bertanggal per lokasi; kontrak/SPK genset; laporan stok BBM", "SPI-10"),
    "M-08": ("Satu sumber otoritatif status alternate: ber-timestamp, TTL maksimum 60 menit, default “not available” bila kedaluwarsa", "Rekayasa informasi", "prevention", "software", "INMC", "PK-7", "Prosedur tertulis; uji fungsi rantai informasi ujung ke ujung", "SPI-12"),
    "M-09": ("Kebijakan bahan bakar kontingensi: extra fuel dan alternate kedua wajib dalam flight planning selama status kontingensi", "Administratif", "recovery", "procedure", "Dir. Operasi & Ditjen Hubud", "PK-3", "Surat edaran bersama DKUPPU–operator; konfirmasi penerapan oleh maskapai", ""),
    "M-10": ("Rencana remote parking dan penggunaan taxiway sebagai stand, dengan kajian keselamatan tersendiri per aerodrome", "Rekayasa", "recovery", "hardware", "Operator Bandara & Kepala Unit", "PK-4", "Kajian per aerodrome disetujui; marka dan prosedur marshalling siap", ""),
    "M-11": ("SOP kontingensi H24 dan penerimaan diversion massal; prosedur degraded mode diuji berkala; butir khusus erupsi pada checklist handover", "Administratif", "prevention", "procedure", "Kepala Unit & Safety Cabang", "PK-8", "SOP terbit dan disosialisasikan; berita acara uji degraded mode", "SPI-14, SPI-15"),
    "M-12": ("Pool rotasi personel antar-cabang untuk S3, terdaftar dan ber-currency; alokasi logistik dan pembiayaan skenario panjang", "Administratif", "prevention", "organisational", "Human Capital & Direksi", "PK-5", "Daftar pool dengan status rating; alokasi anggaran disetujui", "SPI-16"),
    "M-13": ("Prosedur pengukuran friksi dan pelaporan RCR khusus kontaminasi abu pada malam hari; kriteria penutupan runway; kesiapan sweeper", "Rekayasa + prosedur", "prevention", "procedure", "Operator Bandara & Manager KKS", "PK-8", "SOP bersama operator bandara; peralatan tersedia; diuji saat trial", "SPI-13"),
    "M-14": ("Simpul koordinasi cadangan bila JATSC/INMC terdampak; pengujian ATM Contingency Plan untuk skenario ini", "Rekayasa organisasi", "recovery", "organisational", "Dir. Operasi", "PK-8", "Rencana cadangan terbit; berita acara pengujian", "SPI-12"),
    "M-15": ("Kesepakatan tertulis layanan H24 dengan ARFF, Avsec, medis, ground handling, penyedia bahan bakar, BMKG, dan KOBU (LOCA/SLA) beserta readiness confirmation", "Administratif", "prevention", "procedure", "GM Cabang", "PK-8", "LOCA/SLA ditandatangani; angka stok avtur dan inventaris GSE terdokumentasi", ""),
    "M-16": ("Kriteria aktivasi dan terminasi status H24: pemicu, pengambil keputusan, lead time, dan jalur pemberitahuan", "Administratif", "prevention", "procedure", "Dir. Operasi", "PK-8", "Prosedur terbit; diuji pada table-top exercise", ""),
    "M-17": ("Familiarisation dan refresher penanganan beban tinggi serta widebody untuk unit bertraffic rendah; simulasi surge", "Administratif", "prevention", "human", "Manager Operasi", "PK-8", "Catatan pelatihan; hasil simulasi; proficiency check khusus", ""),
    "M-18": ("Penyesuaian jadwal pemeliharaan preventif untuk operasi tanpa jendela shutdown; stok suku cadang kritis di lokasi; perhitungan kapasitas perekaman", "Rekayasa", "prevention", "hardware", "Dir. Teknik", "PK-6", "Jadwal revisi disetujui; daftar stok; perhitungan kapasitas recorder", "SPI-10, SPI-11"),
    "M-19": ("Perpendek interval paper-test selama kontingensi dan tambahkan metode deteksi pelengkap: laporan kru, inspeksi visual runway terjadwal, dan konfirmasi kondisi sebelum kedatangan diversion", "Rekayasa + prosedur", "prevention", "procedure", "Operator Bandara & Manager KKS", "PK-8", "Kesepakatan interval tertulis dengan operator bandara; catatan pelaksanaan; diuji pada operational trial", "SPI-13"),
    "M-20": ("Mekanisme koordinasi formal dengan KOBU: notifikasi keputusan buka/tutup langsung ke INMC dengan target latensi yang disepakati; KOBU ditetapkan sebagai pemasok status resmi bagi sumber otoritatif tunggal (M-08)", "Rekayasa organisasi", "prevention", "organisational", "Dir. Operasi & KOBU", "PK-7", "Nota kesepahaman AirNav–KOBU; bukti uji jalur notifikasi; pengukuran latensi melalui SPI-17", "SPI-17"),
}

PRECONDITIONS = [  # code, text, evidence, owner, main hazard, blocking
    ("PK-1", "Keputusan tertulis mengenai kategori ARFF: peningkatan ke Kategori 9 di WAHI/WICA/WIPP, atau pembatasan tipe pesawat sesuai kategori terpasang", "Surat keputusan Dirjen Hubud / DKUPPU dan berita acara kesiapan operator bandara", "Dir. Operasi & Operator Bandara", "G-01", True),
    ("PK-2", "WICC dan WAHH dicabut dari daftar alternate widebody; batas Code C dipublikasikan eksplisit", "NOTAM/AIP SUP terbit dan terkonfirmasi diterima operator penerbangan", "Dir. Operasi", "G-02", False),
    ("PK-3", "Ditetapkan alternate tambahan di luar kedua sektor sebaran abu (kandidat WARR, WADD, WAAA, WIBB) yang menutup defisit pola terburuk — sekurang-kurangnya 11 posisi Code-E dan 23 posisi Code-C — dengan konfirmasi kesiapan", "Kesepakatan tertulis + readiness confirmation tiap aerodrome", "Direksi", "C-03", True),
    ("PK-4", "Hard cap penerimaan diversion per aerodrome dihitung, disahkan, dan dimuat sebagai parameter operasional di sistem ATFM INMC", "Dokumen perhitungan + bukti konfigurasi sistem + uji fungsi", "INMC & Dir. Operasi", "C-02", True),
    ("PK-5", "Roster H24 tervalidasi model biomatematis; larangan single-manning berlaku; defisit personel dipenuhi dengan penugasan antar-cabang", "Laporan pemodelan fatigue + roster tertandatangani + surat penugasan", "Human Capital & Dir. Operasi", "H-01", False),
    ("PK-6", "Uji beban penuh catu daya (PLN–UPS–genset) di seluruh aerodrome yang dipublikasikan, dengan hasil nominal dan stok BBM minimal 7 hari", "Berita acara pengujian bertanggal per lokasi", "Dir. Teknik", "T-01", False),
    ("PK-7", "Satu sumber otoritatif status ketersediaan alternate dengan time-to-live maksimum 60 menit dan default “not available” bila kedaluwarsa, diberi masukan langsung oleh keputusan KOBU", "Prosedur tertulis + bukti uji fungsi rantai informasi", "INMC", "O-01", False),
    ("PK-8", "Table-top exercise dan operational trial skenario 20 diversion widebody pukul 02.00 dilaksanakan; temuan ditutup", "Berita acara latihan + daftar temuan berstatus closed", "Safety Cabang & Dir. Operasi", "G-04", False),
]


def _bowtie():
    B = {}
    def bar(bid, text, kind, eff, owner, verification, spi="", critical=False):
        B[bid] = {"id": bid, "text": text, "kind": kind, "effectiveness": eff, "owner": owner, "critical": critical,
                  "verification": verification, "spi": spi}
    short = {"M-01": "Cabut WICC/WAHH dari alternate widebody; batas Code C", "M-02": "Alternate di luar sektor abu (alternate ke-3 dijamin)",
             "M-03": "Pembatasan tipe / uplift ARFF Kat 9", "M-04": "Hard cap penerimaan di ATFM", "M-05": "Stop-accept otomatis (80% stand)",
             "M-06": "FRMS + larangan single-manning", "M-07": "Genset kedua + uji beban penuh", "M-08": "Verifikasi status real-time, TTL 60 menit",
             "M-09": "Kebijakan extra fuel", "M-10": "Remote / taxiway parking", "M-11": "Prosedur degraded mode", "M-13": "Pengukuran friksi + RCR malam hari"}
    for m, label in short.items():
        _t, _h, _side, kind, owner, pk, _v, spi = MITIGATIONS[m]
        bar(m, f"{m} {label}", kind, "unknown", owner, "planned", spi,
            critical=m in ("M-02", "M-04", "M-03", "M-08", "M-09"))
    bar("RB-ARFF", "ARFF standby", "human-hardware", "poor", "Operator Bandara", "existing-unverified", "SPI-01")
    bar("RB-STCA", "TCAS / STCA", "hardware", "good", "Dir. Teknik", "existing-verified", "SPI-09")
    bar("RB-EMER", "Emergency procedure", "procedure", "good", "Kepala Unit", "existing-verified")
    bar("RB-RWY", "Kriteria penutupan runway", "procedure", "poor", "Operator Bandara", "existing-unverified", "SPI-13")
    return {
        "hazard": "Operasi H24 aerodrome alternate saat WIII ditutup akibat erupsi Gunung Anak Krakatau",
        "top_event": "Pesawat tidak dapat mendarat dengan selamat di aerodrome alternate",
        "threats": [
            {"id": "T1", "text": "E-01 Alternate di area abu yang sama dengan WIII", "barriers": ["M-02", "M-08"]},
            {"id": "T2", "text": "C-01/C-02 Saturasi stand tanpa hard cap", "barriers": ["M-04", "M-05"]},
            {"id": "T3", "text": "G-01/G-02 Aerodrome tidak layak untuk kelas pesawat", "barriers": ["M-01", "M-03"]},
            {"id": "T4", "text": "H-01/H-02 Fatigue dan single-manning", "barriers": ["M-06"]},
            {"id": "T5", "text": "T-01 Catu daya belum teruji", "barriers": ["M-07"]},
            {"id": "T6", "text": "E-02 Kontaminasi runway oleh abu", "barriers": ["M-13"]},
        ],
        "consequences": [
            {"id": "K1", "text": "Fuel exhaustion", "severity": "A", "barriers": ["M-09", "M-02"]},
            {"id": "K2", "text": "Runway incursion", "severity": "B", "barriers": ["M-10"]},
            {"id": "K3", "text": "Runway excursion", "severity": "B", "barriers": ["RB-ARFF", "RB-RWY"]},
            {"id": "K4", "text": "Loss of separation", "severity": "B", "barriers": ["RB-STCA", "RB-EMER"]},
            {"id": "K5", "text": "Hilangnya pelayanan ATS", "severity": "B", "barriers": ["M-11"]},
        ],
        "barriers": B,
        "escalation": [
            {"id": "EF1", "text": "Erupsi berkepanjangan (S3) — erosi barrier", "barrier": "M-06", "ef_barriers": ["M-12 Pool rotasi personel", "SPI-11 s.d. SPI-14"]},
            {"id": "EF2", "text": "JATSC/INMC ikut terdampak (O-06)", "barrier": "M-04", "ef_barriers": ["M-14 Simpul koordinasi cadangan"]},
            {"id": "EF3", "text": "Operasi malam hari dan cuaca buruk", "barrier": "M-13", "ef_barriers": ["M-19 Deteksi pelengkap (laporan kru, inspeksi visual)"]},
        ],
    }


def _stpa():
    return {
        "losses": [{"id": "L-1", "text": "Kecelakaan pesawat akibat fuel exhaustion setelah diversion"},
                   {"id": "L-2", "text": "Kecelakaan saat pendaratan di alternate (runway excursion / incursion)"},
                   {"id": "L-3", "text": "Hilangnya pelayanan ATS pada saat paling dibutuhkan"}],
        "hazards": [{"id": "H-1", "text": "Pesawat diarahkan ke alternate yang tidak tersedia atau statusnya sudah berubah", "losses": ["L-1"]},
                    {"id": "H-2", "text": "Pesawat mendarat pada runway yang terkontaminasi abu yang belum terdeteksi", "losses": ["L-2"]},
                    {"id": "H-3", "text": "Aerodrome menerima diversion melampaui kapasitas yang dapat ditangani", "losses": ["L-2", "L-3"]}],
        "constraints": [{"id": "SC-1", "text": "Status alternate yang dipakai untuk keputusan harus berasal dari satu sumber otoritatif dan tidak kedaluwarsa", "hazards": ["H-1"]},
                        {"id": "SC-2", "text": "Kontaminasi abu pada runway harus terdeteksi sebelum diversion tiba", "hazards": ["H-2"]},
                        {"id": "SC-3", "text": "Penerimaan diversion tidak boleh melampaui batas yang ditegakkan sistem", "hazards": ["H-3"]}],
        "structure": {"nodes": [
            {"id": "VAAC", "label": "VAAC Darwin", "kind": "controller", "x": 0, "y": 0, "process_model": "Prakiraan sebaran abu (model)"},
            {"id": "AIRNAV", "label": "AirNav Indonesia (ASHTAM)", "kind": "controller", "x": 0, "y": 150, "process_model": "Polygon sebaran; daftar bandara kandidat"},
            {"id": "OPBU", "label": "Operator bandar udara", "kind": "controller", "x": 0, "y": 300, "process_model": "Hasil paper-test periodik"},
            {"id": "KOBU", "label": "KOBU (Kantor Otoritas Bandar Udara)", "kind": "controller", "x": 380, "y": 150, "process_model": "Status buka/tutup bandara"},
            {"id": "INMC", "label": "JATSC / INMC (ATFM)", "kind": "controller", "x": 380, "y": 300, "process_model": "Status alternate; kapasitas penerimaan"},
            {"id": "ATS", "label": "Unit ATS alternate (TWR/APP)", "kind": "controller", "x": 380, "y": 450, "process_model": "Stand tersedia; runway status"},
            {"id": "AO", "label": "Operator penerbangan / pilot", "kind": "controller", "x": 0, "y": 600, "process_model": "Alternate dalam flight plan; bahan bakar"},
            {"id": "AC", "label": "Pesawat diversion", "kind": "process", "x": 190, "y": 760}],
            "edges": [
                {"id": "e1", "source": "VAAC", "target": "AIRNAV", "kind": "control", "label": "Volcanic Ash Advisory"},
                {"id": "e2", "source": "AIRNAV", "target": "OPBU", "kind": "control", "label": "ASHTAM (kandidat dalam polygon)"},
                {"id": "e3", "source": "OPBU", "target": "KOBU", "kind": "feedback", "label": "hasil paper-test"},
                {"id": "e4", "source": "KOBU", "target": "INMC", "kind": "control", "label": "keputusan tutup/buka → NOTAM"},
                {"id": "e5", "source": "INMC", "target": "ATS", "kind": "control", "label": "alokasi diversion; hard cap"},
                {"id": "e6", "source": "ATS", "target": "INMC", "kind": "feedback", "label": "okupansi stand; kesiapan"},
                {"id": "e7", "source": "INMC", "target": "AO", "kind": "control", "label": "status alternate"},
                {"id": "e8", "source": "ATS", "target": "AO", "kind": "control", "label": "clearance; penerimaan"},
                {"id": "e9", "source": "AO", "target": "AC", "kind": "control", "label": "keputusan diversion"},
                {"id": "e10", "source": "AC", "target": "AO", "kind": "feedback", "label": "sisa bahan bakar"}]},
        "ucas": [
            {"id": "UCA-1", "control_action": "keputusan tutup/buka → NOTAM", "type": "Too early / too late / wrong order", "text": "Keputusan penutupan sampai ke INMC setelah pesawat berkomitmen ke alternate", "context": "ketika latensi rantai VAAC → ASHTAM → paper-test → KOBU → NOTAM melampaui waktu terbang (O-10)", "hazards": ["H-1"]},
            {"id": "UCA-2", "control_action": "keputusan tutup/buka → NOTAM", "type": "Providing causes hazard", "text": "Alternate ditutup oleh KOBU tanpa notifikasi langsung ke INMC", "context": "ketika kewenangan berada di luar batas kendali ATS (O-09)", "hazards": ["H-1"]},
            {"id": "UCA-3", "control_action": "status alternate", "type": "Providing causes hazard", "text": "INMC menyampaikan status alternate yang sudah kedaluwarsa", "context": "ketika status tidak memiliki timestamp maupun batas kedaluwarsa (O-01)", "hazards": ["H-1"]},
            {"id": "UCA-4", "control_action": "alokasi diversion; hard cap", "type": "Providing causes hazard", "text": "Diversion diterima berdasarkan data kesiapan yang berumur beberapa jam", "context": "ketika koordinasi hanya lisan melalui supervisor (O-02)", "hazards": ["H-1", "H-3"]},
            {"id": "UCA-5", "control_action": "alokasi diversion; hard cap", "type": "Stopped too soon / applied too long", "text": "Penerimaan diversion tidak dihentikan saat stand jenuh", "context": "ketika tidak ada hard cap yang ditegakkan sistem (C-02)", "hazards": ["H-3"]},
            {"id": "UCA-6", "control_action": "hasil paper-test", "type": "Not providing causes hazard", "text": "Kontaminasi abu tidak dilaporkan sebelum diversion tiba", "context": "ketika paper-test periodik dan abu datang di antara dua uji (E-05), atau abu tipis tidak terdeteksi (E-06)", "hazards": ["H-2"]},
        ],
        "scenarios": [
            {"id": "S-1", "uca": "UCA-1", "type": "Inadequate feedback", "text": "Setiap langkah rantai empat organisasi menambah latensi; tidak ada target maupun pengukuran", "requirement": "M-20 notifikasi formal KOBU → INMC dengan target latensi; SPI-17"},
            {"id": "S-2", "uca": "UCA-3", "type": "Flawed process model", "text": "INMC dan operator menganggap status terakhir masih berlaku", "requirement": "M-08 sumber otoritatif tunggal, TTL 60 menit, default “not available”"},
            {"id": "S-3", "uca": "UCA-5", "type": "Inadequate control algorithm", "text": "Keputusan menerima diambil per kejadian oleh manusia tanpa batas numerik", "requirement": "M-04 hard cap sebagai parameter ATFM; M-05 stop-accept pada 80% okupansi"},
            {"id": "S-4", "uca": "UCA-6", "type": "Inadequate feedback", "text": "Interval paper-test tidak ditetapkan untuk kontingensi; satu jenis uji saja", "requirement": "M-19 interval diperpendek + deteksi pelengkap; M-13 pengukuran friksi/RCR"},
        ],
    }


# Fault tree — ATS power supply over a 30-day contingency horizon (SRA §4.2.4)
FTA_CURRENT = {"top": "TOP", "nodes": {
    "TOP": {"type": "and", "label": "ATS blackout (30 hari) — genset tunggal belum diuji (kondisi WAHS)", "children": ["E1", "E2"]},
    "E1": {"type": "basic", "label": "Gangguan PLN (2 kejadian/tahun/lokasi, 30 hari)", "p": 0.152},
    "E2": {"type": "basic", "label": "Genset tunggal gagal start (belum teruji, 3%/demand)", "p": 0.03},
}}
FTA_TARGET = {"top": "TOP", "nodes": {
    "TOP": {"type": "and", "label": "ATS blackout (30 hari) — dua genset teruji beban penuh (target PK-6)", "children": ["E1", "G1"]},
    "G1": {"type": "or", "label": "Kedua genset gagal", "children": ["G2", "E5"]},
    "G2": {"type": "and", "label": "Genset 1 dan genset 2 gagal secara independen", "children": ["E3", "E4"]},
    "E1": {"type": "basic", "label": "Gangguan PLN (2 kejadian/tahun/lokasi, 30 hari)", "p": 0.152},
    "E3": {"type": "basic", "label": "Genset 1 gagal start", "p": 0.03},
    "E4": {"type": "basic", "label": "Genset 2 gagal start", "p": 0.03},
    "E5": {"type": "basic", "label": "Common cause kedua genset (faktor 10⁻³, asumsi A-07)", "p": 1e-3},
}}


def _gsn(fta_id, bowtie_id):
    n = [
        {"id": "G0", "type": "goal", "text": "Pengoperasian H24 di aerodrome alternate yang ditetapkan adalah TOLERABLY SAFE untuk skenario S1–S3, dengan syarat prakondisi PK-1 s.d. PK-8 terpenuhi"},
        {"id": "C1", "type": "context", "parent": "G0", "text": "Skenario S1 (6–12 jam), S2 (3–7 hari), S3 (>3 minggu); gelombang desain 72 pesawat (20 widebody / 52 narrow-body)"},
        {"id": "C2", "type": "context", "parent": "G0", "text": "Matriks risiko ICAO Doc 9859 5×5 dengan probabilitas bersyarat pada kontingensi aktif (Bab 4.3)"},
        {"id": "A1", "type": "assumption", "parent": "G0", "text": "A-09: sebaran abu mengikuti pola angin ASHTAM VAWR3751; penutupan mengikuti rantai keputusan Bab 2.4"},
        {"id": "A2", "type": "assumption", "parent": "G0", "text": "A-04/A-05/A-06: okupansi stand 8–24 jam; jumlah stand Code-E; acceptance rate 6/jam — wajib dikonfirmasi"},
        {"id": "S0", "type": "strategy", "parent": "G0", "text": "Argumen dipecah menurut lapis pertahanan: kelayakan, kapasitas, manusia, teknis, informasi, lingkungan, ketahanan organisasi"},
        {"id": "G1", "type": "goal", "parent": "S0", "undeveloped": True, "text": "Hanya aerodrome dan kelas pesawat yang memenuhi kriteria adequate aerodrome yang dipublikasikan sebagai alternate [G-01..G-05] — menunggu PK-1, PK-2"},
        {"id": "G2", "type": "goal", "parent": "S0", "undeveloped": True, "text": "Jumlah pesawat yang diterima tidak dapat melampaui kapasitas yang dihitung [C-01..C-06, S-01, S-02] — menunggu PK-4"},
        {"id": "G3", "type": "goal", "parent": "S0", "undeveloped": True, "text": "Pelayanan ATS diberikan tanpa melampaui batas kelelahan dan kompetensi [H-01..H-06] — menunggu PK-5"},
        {"id": "G4", "type": "goal", "parent": "S0", "text": "Fasilitas CNS dan catu daya mempertahankan availability selama operasi kontinu [T-01..T-04]"},
        {"id": "G4.1", "type": "goal", "parent": "G4", "text": "Catu daya WIPP teruji beban penuh; FTA menunjukkan P(blackout) 2,9×10⁻⁴ dengan dua genset teruji"},
        {"id": "Sn1", "type": "solution", "parent": "G4.1", "text": "FTA catu daya (target PK-6)", "evidence": {"kind": "study", "ref": fta_id}},
        {"id": "Sn2", "type": "solution", "parent": "G4.1", "text": "Berita acara uji beban WIPP 1 & 6 Sep 2026", "evidence": {"kind": "document", "ref": "BA uji beban WIPP 01-09-2026 dan 06-09-2026"}},
        {"id": "G4.2", "type": "goal", "parent": "G4", "undeveloped": True, "text": "Seluruh lokasi lain teruji beban penuh; jadwal pemeliharaan direvisi — menunggu PK-6"},
        {"id": "G5", "type": "goal", "parent": "S0", "undeveloped": True, "text": "Status ketersediaan alternate akurat, mutakhir, dan sampai ke pengambil keputusan [O-01, O-02, O-07] — menunggu PK-7"},
        {"id": "G6", "type": "goal", "parent": "S0", "undeveloped": True, "text": "Risiko abu vulkanik pada aerodrome alternate dikelola, bukan diasumsikan tidak ada [E-01..E-04] — menunggu PK-3"},
        {"id": "G7", "type": "goal", "parent": "S0", "text": "Organisasi mampu mempertahankan operasi untuk durasi S3 tanpa degradasi barrier [O-03..O-06, O-08, S-03]"},
        {"id": "G7.1", "type": "goal", "parent": "G7", "text": "Barrier kritis memiliki SPI leading dengan alert level dan eskalasi (Bab 7)"},
        {"id": "Sn3", "type": "solution", "parent": "G7.1", "text": "Bow-tie dengan SPI per barrier", "evidence": {"kind": "study", "ref": bowtie_id}},
        {"id": "G7.2", "type": "goal", "parent": "G7", "undeveloped": True, "text": "SOP kontingensi H24 terbit; pool rotasi dan table-top exercise terlaksana — menunggu PK-8"},
        {"id": "J1", "type": "justification", "parent": "S0", "text": "Lima dari tujuh sub-klaim belum terpenuhi; argumen tidak mendukung GO tanpa syarat (Kejujuran argumen, Bab 5.2)"},
    ]
    return {"nodes": n}


ENVIRONMENT = """Skenario referensi (probabilitas bersyarat pada kontingensi aktif, asumsi A-01):
• S1 Penutupan 6–12 jam — gelombang diversion serentak, saturasi stand.
• S2 Penutupan 3–7 hari — ketahanan pola dinas H24.
• S3 Intermiten >3 minggu — kelelahan organisasi, normalisasi penyimpangan.

Permintaan: WIII 368.017 pergerakan/tahun = 1.008/hari; 504 kedatangan/hari; jam sibuk 38/jam; gelombang 2 jam = 76 → nilai desain 72 pesawat (20 widebody + 52 narrow-body).

Feasibility gate (Annex 6 / Annex 14): tidak ada alternate berkategori ARFF 9 (armada widebody WIII). Widebody: WAHI bersyarat (PK-1), WICA dan WIPP bersyarat (PK-1 dan PK-3), WAHQ/WAHS/WICC/WAHH tidak lulus. Narrow-body: WAHI, WAHQ, WAHS lulus; WICA, WIPP, WICC bersyarat PK-3; WAHH hanya s.d. ARFF Kat 6.

Model kapasitas: saturasi stand WICA 9 stand / 6 per jam = 1,5 jam. Alokasi gelombang ke kapasitas penuh ketujuh alternate: 75 posisi vs 72 (margin 3, 4%); jaringan jenuh dalam 1,1 jam; menyerap 15% kedatangan harian WIII. Pola abu terburuk (WICA, WICC, WIPP keluar): 38 posisi vs 72 → defisit 34 (11 widebody, 23 narrow-body).

Roster H24: Yogyakarta–Solo butuh 42 (tersedia 39, defisit 3); Semarang butuh 16,8 (tersedia 19); Kertajati butuh 8,4 (verifikasi).

Profil risiko (40 hazard): Inherent 21 INT / 19 TOL / 0 ACC; Current 15 INT / 25 TOL / 0 ACC; Residual 0 INT / 24 TOL / 16 ACC (hanya setelah PK-1 s.d. PK-8 dipenuhi dan diverifikasi)."""

ASSUMPTIONS = """A-01 Kontingensi aktif; probabilitas bersyarat pada skenario (Mendasar).
A-02 Kedatangan jam sibuk WIII = 7,5% dari kedatangan harian (Tinggi) — hitung dari jadwal WIII aktual.
A-03 Proporsi widebody pada gelombang diversion = 28% (Tinggi).
A-04 Pesawat diversion menduduki stand 8–24 jam; tidak ada daur ulang stand dalam S1 (Tinggi).
A-05 Jumlah stand total, jumlah Code-E, dan okupansi eksisting per aerodrome (Tinggi) — konfirmasi tertulis operator bandara.
A-06 Acceptance rate realistis unit berpengalaman rendah = 6 kedatangan/jam (Sedang) — uji melalui operational trial (PK-8).
A-07 Laju gangguan PLN = 2 kejadian/tahun/lokasi; kegagalan start genset belum teruji = 3%/demand (Sedang).
A-08 Faktor relief roster = 1,4 (Sedang).
A-09 Sebaran abu mengikuti pola angin ASHTAM VAWR3751; penutupan mengikuti rantai keputusan Bab 2.4 (Tinggi).
A-10 JATSC dan INMC tetap beroperasi selama kontingensi (Tinggi) — lihat hazard O-06.
A-11 Pergerakan 2025 sebagai dasar perhitungan (Tinggi).
A-12 Interval paper-test dan latensi keputusan KOBU memungkinkan status diperbarui sebelum pilot mengambil keputusan (Tinggi) — ukur melalui SPI-17."""


def seed_demo_v3(db: Session):
    if db.query(Project).filter_by(code="DEMO-03").first():
        return
    p = Project(code="DEMO-03", title="Studi kasus — Operasi 24 jam aerodrome alternate (erupsi Gunung Anak Krakatau)",
                change_type="procedure", units=AERODROMES, sponsor="Direktorat Operasi",
                description=f"Worked example from {DOC}: activation of H24 ATS at designated alternate aerodromes when WIII Soekarno–Hatta "
                            "is closed by volcanic ash. Recommendation: CONDITIONAL GO — eight activation preconditions (PK-1 to PK-8).")
    db.add(p); db.flush()
    a = Assessment(project_id=p.id, title="SRA operasi H24 aerodrome alternate — Revisi 00", created_by="assessor",
                   scope="Perubahan: perpanjangan jam pelayanan ATS dari pola terbatas menjadi 24 jam terus-menerus pada cabang/unit yang "
                         "ditetapkan sebagai aerodrome alternate, disertai penerimaan diversion dalam jumlah besar dari WIII. Pemicu: erupsi "
                         "Gunung Anak Krakatau (ASHTAM VAWR3751, 33 aerodrome terdampak). Klasifikasi: major change (Annex 19 / Doc 9859 Bab 9); "
                         "sementara, reversibel, aktivasi berbasis pemicu.\n\nDi dalam lingkup: pelayanan ATS, personel ATC/ACO/CNS, fasilitas CNS, "
                         "catu daya fasilitas ATS, prosedur lokal dan handover, ATFM melalui INMC, publikasi NOTAM. Di luar lingkup (antarmuka, "
                         "LOCA/SLA): fasilitas sisi udara dan ARFF (operator bandara), MET (BMKG), bahan bakar dan GSE, ruang udara militer, "
                         "sertifikasi ARFF (DKUPPU).\n\nRekomendasi: CONDITIONAL GO — PK-1, PK-3 dan PK-4 bersifat blocking.",
                   environment=ENVIRONMENT, assumptions=ASSUMPTIONS)
    db.add(a); db.flush()

    def study(method, title, model, results=None):
        s = Study(assessment_id=a.id, method=method, title=title, model=model, results=results or {},
                  participants=[{"name": "Safety Cabang", "role": "Facilitator"}, {"name": "Manager Operasi", "role": "SME"},
                                {"name": "Manager Teknik", "role": "SME"}, {"name": "INMC", "role": "SME"}])
        db.add(s); db.flush(); return s

    rows = []
    for hid, hz, cons, inh, bar, _q, cur, mits, res, _j in HAZARDS:
        rows.append({"id": hid, "guideword": HAZID_GW[hid[0]], "hazard": hz, "causes": f"Inherent (tanpa barrier): {inh}",
                     "consequences": cons, "controls": bar, "severity": cur[1], "likelihood": int(cur[0]),
                     "actions": "; ".join(f"{m} {MITIGATIONS[m][0][:60]}…" for m in mits), "owner": MITIGATIONS[mits[0]][4]})
    reg = study("hazid", "Register risiko — FHA (F1–F7), HAZOP dan STPA, 40 hazard (SRA §4.4)", {"rows": rows})
    stpa = study("stpa", "STPA — rantai keputusan penutupan dan pembukaan bandara (SRA §2.4)", _stpa())
    f1 = study("fta", "FTA — catu daya ATS 30 hari, genset tunggal belum teruji (SRA §4.2.4)", {"tree": FTA_CURRENT}, fta_engine.analyse(FTA_CURRENT))
    f2 = study("fta", "FTA — catu daya ATS 30 hari, dua genset teruji (target PK-6)", {"tree": FTA_TARGET}, fta_engine.analyse(FTA_TARGET))
    bt = study("bowtie", "Bow-tie — pesawat tidak dapat mendarat dengan selamat di alternate (SRA §5.3)", _bowtie())
    study("gsn", "Safety argument — operasi H24 aerodrome alternate (SRA §5.1–5.2)", _gsn(f2.id, bt.id))

    source = {"O-01": stpa.id, "O-02": stpa.id, "O-09": stpa.id, "O-10": stpa.id, "E-05": stpa.id, "E-06": stpa.id, "T-01": f1.id}
    hazards = {}
    for hid, hz, cons, inh, bar, q, cur, mits, res, just in HAZARDS:
        h = Hazard(ref=f"ALT-{hid}", title=hz, consequences=cons, description=hz, context=f"Inherent (tanpa barrier apa pun): {inh}. Probabilitas bersyarat pada kontingensi aktif (A-01).",
                   unit=AERODROMES, system=GROUPS[hid[0]].split(" — ")[1], owner=MITIGATIONS[mits[0]][4], status="open",
                   review_date=REVIEW, assessment_id=a.id, source_study_id=source.get(hid, reg.id), source_row=hid,
                   initial_severity=cur[1], initial_likelihood=int(cur[0]), residual_severity=res[1], residual_likelihood=int(res[0]),
                   rationale=just, evidence=f"{DOC} §4.4 (risk register) dan §6.2 (residual per hazard). Residual berlaku hanya setelah mitigasi berstatus closed-verified.")
        db.add(h); db.flush(); hazards[hid] = h
        if bar and not bar.startswith("Tidak ada"):
            eff = q or "unknown"
            db.add(Control(hazard_id=h.id, text=bar, side="prevention", kind="procedure", effectiveness=eff,
                           verification="existing-verified" if "bukti ada" in bar or eff == "good" else "existing-unverified"))
        for m in mits:
            t, hier, side, kind, owner, pk, ver, spi = MITIGATIONS[m]
            db.add(Control(hazard_id=h.id, text=f"{m} [{hier}] {t} — verifikasi: {ver} ({pk})", side=side, kind=kind, owner=owner,
                           verification="planned", effectiveness="unknown", critical=pk.split(",")[0] in ("PK-1", "PK-3", "PK-4"), spi=spi))
    for code, text, evidence, owner, hid, blocking in PRECONDITIONS:
        db.add(Action(ref=f"ALT-{code}", text=f"{code}{' [BLOCKING]' if blocking else ''}: {text}. Bukti pemenuhan: {evidence}",
                      owner=owner, due_date=REVIEW, hazard_id=hazards[hid].id, assessment_id=a.id, status="open"))
    db.commit()
