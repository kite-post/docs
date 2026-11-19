# 09 · API-контракт

> **Kite** — документація поштової системи · v1.4 · затверджено · 17.11.2026

Зовнішній API — REST/JSON за шлюзом під `/api/v1`, описаний у `openapi.yaml` репозиторію `kite-contracts`; між сервісами — події Kafka у форматі CloudEvents; пристрої — MQTT; живі оновлення — WebSocket. Нижче — правила і повна карта ендпоїнтів; схеми тіл запитів і відповідей — у OpenAPI.

Стан контракту: `kite-contracts` v0.2.0 описує публічну частину й автентифікацію (9.2), клієнтський кабінет (9.3) і з Kite Ops — лише прийом сканів і сортувальну підказку (9.5); разом 41 шлях і 53 операції. Kite Business (9.4) і решта Kite Ops дописуються в контракт разом із відповідними сервісами. Усі 34 типи подій (9.7) уже описані.

## 9.1 Загальні правила

- **Автентифікація:** `Authorization: Bearer <JWT>` для клієнтів і персоналу; `X-Api-Key` для бізнес-інтеграцій (схема оголошена в OpenAPI, до операцій підключається разом із Kite Business).
- **Ідемпотентність:** `Idempotency-Key` (UUID) обов'язковий для створення, підтвердження й скасування відправлень, дій керування доставкою, платежів, відкриття комірки, бронювання камери зберігання і претензій; повтор з тим самим ключем повертає ту саму відповідь 24 год. Пакет сканів ідемпотентний за `scanId` кожного скану.
- **Помилки:** формат `application/problem+json` (RFC 9457) з полями `type`, `title`, `status`, `detail`, `instance`, `code` (наприклад `SHIPMENT_INVALID_TRANSITION`), `requestId` і `errors[]` (`field`, `code`, `message`) для валідації.
- **Пагінація:** курсорна — `?limit=20&cursor=…` (`limit` від 1 до 100, типово 20), у відповіді `nextCursor`.
- **Мова:** `Accept-Language: uk` або `en` — від неї залежать людські описи статусів.
- **Трасування:** `X-Request-Id` приймається або генерується шлюзом і проходить через усі сервіси й події.
- **Конкурентні зміни:** `ETag` / `If-Match` для PATCH профілю (`/me`) і відправлень; PATCH всюди має семантику злиття (RFC 7396) — поля, яких немає в тілі, лишаються як були. Налаштування сповіщень замінюються цілком через PUT.
- **Вебхуки бізнесу:** заголовок `Kite-Signature: t=<час>,v1=<HMAC-SHA256(secret, t.body)>`; повтори з експоненційною паузою до 24 год.

## 9.2 Публічні та автентифікація

| Метод і шлях                              | Призначення                                                                | Доступ               |
| ----------------------------------------- | -------------------------------------------------------------------------- | -------------------- |
| POST /api/v1/auth/otp                     | Надіслати код на телефон                                                   | Публічно, rate limit |
| POST /api/v1/auth/otp/verify              | Перевірити код, отримати токени                                            | Публічно             |
| POST /api/v1/auth/refresh                 | Оновити токен                                                              | Refresh token        |
| GET /api/v1/public/track/{trackingNumber} | Публічний статус без персональних даних                                    | Публічно             |
| GET /api/v1/public/locations              | Точки на карті: bbox, тип, послуги, відкрито зараз, вільний розмір комірки | Публічно             |
| GET /api/v1/public/locations/{id}         | Картка точки                                                               | Публічно             |
| POST /api/v1/public/quotes                | Калькулятор вартості                                                       | Публічно             |

## 9.3 Клієнт

| Метод і шлях                                                                                   | Призначення                                            |
| ---------------------------------------------------------------------------------------------- | ------------------------------------------------------ |
| GET, PATCH /api/v1/me                                                                          | Профіль, мова, тема, тиха година                       |
| GET, POST /api/v1/me/phones; POST …/{id}/verify; POST …/{id}/activate; DELETE …/{id}           | Мультиномер                                            |
| GET, POST, DELETE /api/v1/me/trusted-persons                                                   | Довірені особи                                         |
| GET, POST, PATCH, DELETE /api/v1/me/favorite-locations                                         | Улюблені точки                                         |
| GET, PUT /api/v1/me/notification-preferences                                                   | Налаштування сповіщень                                 |
| POST, DELETE /api/v1/me/push-subscriptions                                                     | Підписка web push або FCM                              |
| POST /api/v1/shipments                                                                         | Створити чернетку або одразу підтверджене відправлення |
| GET /api/v1/shipments?direction=incoming\|outgoing\|archive                                    | Дашборд «мені / від мене / архів»                      |
| GET, PATCH /api/v1/shipments/{id}                                                              | Деталі; зміна чернетки                                 |
| POST /api/v1/shipments/{id}/confirm                                                            | DRAFT → CREATED                                        |
| POST /api/v1/shipments/{id}/cancel                                                             | Скасування до прийому                                  |
| GET /api/v1/shipments/{id}/qr                                                                  | QR для відправки без етикетки (SVG)                    |
| GET /api/v1/shipments/{id}/timeline                                                            | Таймлайн подій і прогноз                               |
| GET /api/v1/shipments/{id}/actions                                                             | Доступні дії з цінами для поточного стану              |
| POST /api/v1/shipments/{id}/actions/{redirect\|hold\|change-recipient\|extend-storage\|refuse} | Керування доставкою                                    |
| POST /api/v1/payments; GET /api/v1/payments/{id}                                               | Оплата: повертає `redirectUrl` на сторінку mock-pay    |
| POST /api/v1/lockers/{locationId}/open                                                         | Відкрити комірку (отримання або відправка)             |
| POST, GET /api/v1/storage-bookings                                                             | Камера зберігання в Kite Box                           |
| GET, POST, DELETE /api/v1/me/external-tracking                                                 | Сторонні номери                                        |
| POST, GET /api/v1/claims; POST /api/v1/claims/{id}/attachments                                 | Претензії; посилання для завантаження фото             |
| GET /api/v1/me/bonuses; POST /api/v1/promo-codes/validate                                      | Бали і промокоди                                       |
| GET, POST /api/v1/tickets; POST /api/v1/tickets/{id}/messages                                  | Підтримка                                              |

## 9.4 Kite Business

| Метод і шлях                                                         | Призначення                   |
| -------------------------------------------------------------------- | ----------------------------- |
| GET, PATCH /api/v1/business/org                                      | Організація, реквізити, план  |
| GET, POST, PATCH, DELETE /api/v1/business/members                    | Учасники і ролі               |
| GET, POST, DELETE /api/v1/business/api-keys                          | Ключі API                     |
| GET, POST, PATCH, DELETE /api/v1/business/webhooks; POST …/{id}/test | Вебхуки                       |
| POST /api/v1/business/imports; GET …/{id}; GET …/{id}/report         | Імпорт CSV і звіт про помилки |
| POST, GET /api/v1/business/registries; GET …/{id}/pdf                | Реєстри приймання-передачі    |
| GET /api/v1/business/invoices; GET /api/v1/business/cod-payouts      | Рахунки і виплати післяплати  |
| GET /api/v1/business/analytics                                       | Зведення за період            |
| POST /api/v1/business/returns/settings                               | Налаштування легких повернень |

Відправлення бізнес створює тим самим `POST /api/v1/shipments` — з ключем API організації.

## 9.5 Kite Ops (персонал)

| Метод і шлях                                                                   | Призначення                                                        | Роль                       |
| ------------------------------------------------------------------------------ | ------------------------------------------------------------------ | -------------------------- |
| GET /api/v1/ops/shipments/search?q=                                            | Пошук за номером, телефоном, ПІБ                                   | Оператор, підтримка        |
| POST /api/v1/ops/acceptances                                                   | Прийом: штрих-код, фактична вага, габарити, оплата на касі         | Оператор                   |
| GET /api/v1/ops/shipments/{id}/label                                           | Етикетка PDF                                                       | Оператор                   |
| POST /api/v1/ops/handovers                                                     | Видача: код отримувача або довірена особа                          | Оператор                   |
| POST /api/v1/scans                                                             | Пакет сканів (до 100)                                              | Будь-який сканер персоналу |
| GET /api/v1/ops/hubs/{hubId}/sort-hint/{barcode}                               | Сортувальна підказка                                               | Сортувальник               |
| POST /api/v1/ops/units; POST …/{id}/items; POST …/{id}/close; POST …/{id}/open | Мішки й контейнери                                                 | Сортувальник, оператор     |
| POST /api/v1/ops/trips; POST …/{id}/{start-loading\|depart\|arrive}            | Рейси                                                              | Начальник зміни, водій     |
| GET /api/v1/ops/trips/{id}/manifest; GET …/{id}/reconciliation                 | Маніфест і звірка                                                  | Начальник зміни            |
| GET, PATCH /api/v1/ops/discrepancies                                           | Розбіжності                                                        | Начальник зміни            |
| POST /api/v1/ops/scanner-sessions                                              | Почати пейринг: код і QR для телефону                              | Персонал                   |
| POST /api/v1/scanner/pair                                                      | Телефон приєднується до сесії                                      | Персонал                   |
| CRUD /api/v1/ops/locations, /routing-rules, /sort-lines, /schedules            | Мережа                                                             | Адмін                      |
| CRUD /api/v1/ops/tariffs, /promo-codes                                         | Тарифи і промокоди                                                 | Адмін                      |
| CRUD /api/v1/ops/users                                                         | Персонал, ролі й прив'язка до точки (фасад над Keycloak і network) | Адмін                      |
| GET /api/v1/ops/incidents; GET /api/v1/ops/network/load                        | Диспетчерська                                                      | Диспетчер                  |
| GET, PATCH /api/v1/ops/claims; /api/v1/ops/tickets                             | Претензії і тікети                                                 | Підтримка                  |
| GET /api/v1/ops/audit                                                          | Журнал дій                                                         | Адмін                      |

## 9.6 Реальний час і пристрої

| Канал     | Адреса                       | Що передає                                                       |
| --------- | ---------------------------- | ---------------------------------------------------------------- |
| WebSocket | /ws/client                   | Оновлення таймлайну і статусів для клієнта                       |
| WebSocket | /ws/ops                      | Скани з телефону, сортувальні підказки, інциденти                |
| WebSocket | /ws/scanner                  | Телефон-сканер: надсилає скани, отримує підказки й вібро-сигнали |
| MQTT      | kite/box/{lockerId}/cmd/open | Команда відкрити комірку                                         |
| MQTT      | kite/box/{lockerId}/evt/door | Двері відкрито / закрито, датчик заповнення                      |
| MQTT      | kite/scanner/{deviceId}/scan | Скани зі стаціонарного сканера-заглушки                          |

## 9.7 Події Kafka

Усі події — CloudEvents 1.0 у JSON. Обов'язкові поля конверта — `specversion`, `id` (UUID), `source`, `type`, `time` і `data`; необов'язкові — `subject`, `datacontenttype`, `dataschema` і власні розширення `kitereceivedat` (час запису), `kiterequestid` (`X-Request-Id`), `kitecausationid` (подія-причина) і `kitepartitionkey`. Тип події — `kite.<домен>.<подія>.v1`; топік, продюсер, споживачі й ключ розділу кожного типу задані в `events/registry.json` репозиторію `kite-contracts`. Для подій відправлення ключ розділу — `shipmentId`.

| Топік            | Типи подій                                                                                                                                                                                                                                                     | Ключ розділу                                          | Продюсер          | Споживачі                                                              |
| ---------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------- | ----------------- | ---------------------------------------------------------------------- |
| shipment.events  | `kite.shipment.created.v1`, `kite.shipment.confirmed.v1`, `kite.shipment.cancelled.v1`, `kite.shipment.status-changed.v1`, `kite.shipment.redirected.v1`, `kite.shipment.recipient-changed.v1`, `kite.shipment.hold-set.v1`, `kite.shipment.return-created.v1` | `shipmentId`; return-created — `originalShipmentId`   | shipment-service  | tracking, notification, payment, locker, business (вебхуки), ai, audit |
| scan.events      | `kite.scan.recorded.v1`, `kite.scan.unit-scanned.v1`, `kite.scan.voided.v1`                                                                                                                                                                                    | `shipmentId`; unit-scanned — `unitCode`               | scan-service      | shipment, logistics, tracking, realtime                                |
| logistics.events | `kite.logistics.unit-closed.v1`, `kite.logistics.trip-departed.v1`, `kite.logistics.trip-arrived.v1`, `kite.logistics.discrepancy-opened.v1`                                                                                                                   | unit-closed — `unitCode`; решта — `tripId`            | logistics-service | shipment, tracking, realtime                                           |
| locker.events    | `kite.locker.cell-reserved.v1`, `kite.locker.parcel-deposited.v1`, `kite.locker.parcel-collected.v1`, `kite.locker.storage-expired.v1`                                                                                                                         | `shipmentId`                                          | locker-service    | shipment, tracking, notification                                       |
| payment.events   | `kite.payment.succeeded.v1`, `kite.payment.failed.v1`, `kite.payment.refund-completed.v1`, `kite.payment.cod-collected.v1`, `kite.payment.payout-completed.v1`                                                                                                 | `shipmentId`; payout-completed — `payoutId`           | payment-service   | shipment, notification, business                                       |
| customer.events  | `kite.customer.phone-verified.v1`, `kite.customer.phone-removed.v1`, `kite.customer.trusted-person-changed.v1`                                                                                                                                                 | `customerId`                                          | customer-service  | tracking (індекс «мені»), shipment                                     |
| ai.events        | `kite.ai.eta-predicted.v1`, `kite.ai.risk-scored.v1`                                                                                                                                                                                                           | `shipmentId`                                          | ai-service        | tracking, notification, shipment                                       |
| care.events      | `kite.care.claim-created.v1`, `kite.care.claim-resolved.v1`, `kite.care.ticket-updated.v1`                                                                                                                                                                     | `shipmentId`; ticket-updated — `ticketId`             | care-service      | notification, payment (компенсація)                                    |
| audit.events     | `kite.audit.staff-action.v1`, `kite.audit.pii-accessed.v1`                                                                                                                                                                                                     | staff-action — `entityId`; pii-accessed — `subjectId` | усі сервіси       | audit-service                                                          |

---

[← 08 · Подієва модель відстеження](../04-domen/08-podiieva-model-vidstezhennia.md) · [Зміст](../README.md) · [10 · Сканування і заглушки →](10-skanuvannia-i-zahlushky.md)
