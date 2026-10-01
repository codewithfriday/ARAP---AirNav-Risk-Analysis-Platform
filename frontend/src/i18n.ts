import i18n from 'i18next'
import { initReactI18next } from 'react-i18next'

const en = {
  nav: { dashboard: 'Dashboard', projects: 'Projects & assessments', hazards: 'Hazard log', actions: 'Actions', cases: 'Case library',
    scheme: 'Risk scheme', users: 'Users', audit: 'Audit trail', guide: 'User guide' },
  common: { save: 'Save', saved: 'Saved', cancel: 'Cancel', add: 'Add', delete: 'Delete', edit: 'Edit', create: 'Create',
    calculate: 'Calculate', export: 'Export', search: 'Search', status: 'Status', owner: 'Owner', title: 'Title',
    locked: 'Locked — create a new version to change', logout: 'Sign out', language: 'Language', none: 'None',
    readonly: 'Read-only', promote: 'Send to hazard log', results: 'Results', help: 'Manual chapter' },
  login: { title: 'Sign in to NAVRAP', username: 'Username', password: 'Password', submit: 'Sign in',
    subtitle: 'AirNav Risk Analysis Platform' },
  dash: { hazards: 'Hazards in log', overdue: 'Overdue actions', reviews: 'Reviews due (30 days)', inReview: 'Assessments in review',
    matrix: 'Current risk profile', byRegion: 'Hazards by risk region', byMethod: 'Studies by method', byStatus: 'Assessments by status',
    barriers: 'Controls by effectiveness' },
}

const id: typeof en = {
  nav: { dashboard: 'Dasbor', projects: 'Proyek & penilaian', hazards: 'Log bahaya', actions: 'Tindakan', cases: 'Pustaka kasus',
    scheme: 'Skema risiko', users: 'Pengguna', audit: 'Jejak audit', guide: 'Panduan pengguna' },
  common: { save: 'Simpan', saved: 'Tersimpan', cancel: 'Batal', add: 'Tambah', delete: 'Hapus', edit: 'Ubah', create: 'Buat',
    calculate: 'Hitung', export: 'Ekspor', search: 'Cari', status: 'Status', owner: 'Pemilik', title: 'Judul',
    locked: 'Terkunci — buat versi baru untuk mengubah', logout: 'Keluar', language: 'Bahasa', none: 'Tidak ada',
    readonly: 'Hanya baca', promote: 'Kirim ke log bahaya', results: 'Hasil', help: 'Bab manual' },
  login: { title: 'Masuk ke NAVRAP', username: 'Nama pengguna', password: 'Kata sandi', submit: 'Masuk',
    subtitle: 'Platform Analisis Risiko AirNav' },
  dash: { hazards: 'Bahaya dalam log', overdue: 'Tindakan terlambat', reviews: 'Tinjauan jatuh tempo (30 hari)', inReview: 'Penilaian dalam tinjauan',
    matrix: 'Profil risiko saat ini', byRegion: 'Bahaya per wilayah risiko', byMethod: 'Studi per metode', byStatus: 'Penilaian per status',
    barriers: 'Kontrol per efektivitas' },
}

let lng = 'en'
try {
  lng = localStorage.getItem('arap_lang') || 'en'
} catch {
  /* ignore */
}

i18n.use(initReactI18next).init({ resources: { en: { translation: en }, id: { translation: id } }, lng, fallbackLng: 'en',
  interpolation: { escapeValue: false } })

export default i18n
