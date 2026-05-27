# Telefon ile localhost testi

## Hızlı yol (önerilen)

1. Backend ve frontend’i başlatın (README).
2. [ngrok](https://ngrok.com) kurun ve frontend portunu açın:

```bash
ngrok http 5173
```

3. Telefonda ngrok’un verdiği `https://....ngrok-free.app` adresini açın.
4. Vite, `/api` isteklerini bilgisayarınızdaki `127.0.0.1:8000` adresine yönlendirir; ekstra API tüneli gerekmez.

**Not:** Telefon ve PC aynı Wi‑Fi’da olmalı; ngrok trafiği PC’nize gelir.

## Alternatif: sadece API tüneli

1. `ngrok http 8000`
2. `frontend/.env` dosyası oluşturun:

```
VITE_API_URL=https://YOUR-NGROK-ID.ngrok-free.app
```

3. Frontend’i yeniden başlatın (`npm run dev`).

## PWA ana ekrana ekleme

- **iOS Safari:** Paylaş → Ana Ekrana Ekle
- **Android Chrome:** Menü → Uygulamayı yükle / Ana ekrana ekle

HTTPS (ngrok) PWA kurulumu için gereklidir.

## Sorun giderme

| Sorun | Çözüm |
|--------|--------|
| API bağlanmıyor | Backend’in `0.0.0.0:8000` dinlediğinden emin olun |
| CORS hatası | `backend/.env` içine ngrok frontend URL’sini `CORS_ORIGINS`’e ekleyin |
| Tahta bulunamadı | Tam ekran SS; tahta + 3 taş görünsün |
