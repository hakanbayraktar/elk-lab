#!/usr/bin/env bash
echo ">>> Uygulamalara trafik gönderiliyor..."
for i in {1..10}; do
  curl -s http://localhost:8081/ >/dev/null || true
  curl -s http://localhost:8081/non-existent-page.html >/dev/null || true
  curl -s http://localhost:3001/api/pay >/dev/null || true
  curl -s http://localhost:3001/api/fail >/dev/null || true
done
echo ">>> 40 istek başarıyla gönderildi (200, 404, 500)."
