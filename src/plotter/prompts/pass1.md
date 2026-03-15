# Промпт: Проход 1 — Извлечение сюжетных линий

> **Самостоятельный документ.** Собран из справочника `storyline-extraction-reference.md`, но подаётся в LLM как есть. При обновлении reference — пересобрать.

## Контракт

- **Вход**: выход Pass 0 (`show`, `season`, `franchise_type`, `story_engine`) + все синопсисы сезона
- **Выход**: JSON со списком линий и кастом → передаётся как вход в Pass 2

## Вход

- **show**: название шоу (из Pass 0)
- **season**: номер сезона (из Pass 0)
- **franchise_type**: procedural / serial / hybrid / ensemble (из Pass 0)
- **story_engine**: одно предложение (из Pass 0)
- **format**: ongoing / limited / anthology / null (из Pass 0)
- **synopses**: все синопсисы сезона (текст)

## Задача

Прочитай ВСЕ синопсисы сезона. Извлеки список сюжетных линий и основной каст.

## Правила

### Линия = Story DNA

Линия = hero + goal + obstacle + stakes. Нет любого компонента — не линия, а событие внутри другой линии.

Дополнительно: у линии есть трёхактная структура, конфликт, каузальная цепь событий. Линия привязана к персонажу основного каста (не гостевого).

### Типы линий

- **Episodic** — закрывается в каждом эпизоде. Для procedural/hybrid: создай ОДНУ episodic-линию для franchise engine (case-of-week). Story DNA шаблонная (повторяющаяся цель/obstacle/stakes), конкретное наполнение — в Pass 2.
- **Serialized** — тянется через несколько эпизодов или весь сезон.
- **Runner** — нет obstacle или resolution, логлайн описательный. Всё остальное — полноценная линия.

### Иерархия A/B/C

Каждой линии присвой rank — её типичную роль через сезон:

- **A** — линия протагониста или franchise engine, максимум экранного времени, plot-led конфликт
- **B** — вторая по значимости, часто character-led, несёт тему эпизода
- **C** — третья, легче по тону, меньше экранного времени
- **runner** — неполная Story DNA, нет obstacle/resolution

Для serial/ensemble rank может меняться от эпизода к эпизоду (линия — A в одном, B в другом). Здесь указывай типичный rank через сезон. Pass 2 может переопределить per episode.

В procedural/hybrid: episodic-линия (franchise engine) = всегда A.

### По характеру конфликта

- **Plot-led** — внешняя цель vs антагонист.
- **Character-led** — внутренний конфликт, протагонист = собственный антагонист.

### Seed и wraparound — не типы линий

Seed — function события в Pass 2. Wraparound — мета-приём в Pass 2. Не создавай линии этих типов.

### Гранулярность

Ключ — ЦЕЛЬ, не персонаж. Один персонаж может вести несколько линий с разными целями.

Одна линия: один driver + одна цель + каузальная связь.
Разные линии: разные drivers, ИЛИ один driver с разными целями, ИЛИ нет каузальной связи.

Тест: если нельзя написать логлайн (герой + цель + препятствие) — не линия.

### Что НЕ линия

| пример | что это |
|--------|---------|
| «Джон обедает» | Фон — нет цели/конфликта |
| «Все идут на вечеринку» | Сеттинг — нет driver/stakes |
| «Джон грустит» | Состояние — нет цели/obstacle |
| «Дружба Джона и Майка» | Контекст — нет конфликта |
| «Расследование» (процедурал, эп.5) | Franchise engine — часть episodic-линии |

Сомневаешься — НЕ создавай линию.

### Неполные синопсисы

Story DNA восстанавливается из совокупности упоминаний через сезон. Не выдумывай — помечай confidence.

### Именование

Имя = абстрактное слово по ЦЕЛИ, не по событию. Episodic-линия (franchise engine): назови по формуле franchise — «Case of the Week», «Crime of the Week», «Mission» и т.п. — чтобы было сразу понятно, что это повторяющаяся структура. Всегда используй формат `Driver: Theme` для имён линий (напр. "House: Authority", "Cameron: Ethics", "Jon: Honor"). Это делает явным кто ведёт каждую линию и предотвращает путаницу при распределении событий.

### Нарративные приёмы (devices)

Читая синопсисы, отмечай если линия использует повторяющиеся нарративные приёмы. Запиши их в поле `devices`. У большинства линий приёмов нет — оставь пустой список.

| приём | что означает |
|-------|-------------|
| `dramatic_irony` | зритель знает то, чего не знают персонажи этой линии |
| `flashback` | события этой линии показаны не в хронологическом порядке (прошлое) |
| `flashforward` | события этой линии показаны не в хронологическом порядке (будущее) |
| `callback` | эта линия реализует то, что было заложено ранее |
| `twist` | эта линия содержит откровение, меняющее понимание зрителя |
| `unreliable` | события этой линии искажены рассказчиком или точкой зрения |

Указывай только приёмы, **характерные** для линии через весь сезон, не разовые.

### Формат сериала и resolution

- **ongoing**: линии могут тянуться за пределы сезона, cliffhanger в финале допустим.
- **limited**: все линии должны получить resolution внутри сезона.
- **anthology**: каждый сезон независим, не ссылайся на другие сезоны.

### Количественные ожидания

- Procedural: 2–3 линии на эпизод (1 episodic + 1–2 serialized).
- Serial: 3–8 сквозных линий на сезон.
- Ensemble: 4–6 параллельных линий.

## Формат выхода

Ответ — строго JSON, без markdown-обёртки, без комментариев вне JSON.

```json
{
  "show": "Breaking Bad",
  "season": 1,
  "cast": [
    {"id": "walt", "name": "Walter White", "aliases": ["Walt", "Heisenberg", "Mr. White"]},
    {"id": "jesse", "name": "Jesse Pinkman", "aliases": ["Jesse", "Cap'n Cook"]},
    {"id": "hank", "name": "Hank Schrader", "aliases": ["Hank"]},
    {"id": "skyler", "name": "Skyler White", "aliases": ["Skyler"]},
    {"id": "tuco", "name": "Tuco Salamanca", "aliases": ["Tuco"]}
  ],
  "storylines": [
    {
      "id": "empire",
      "name": "Walt: Empire",
      "driver": "walt",
      "goal": "построить наркобизнес",
      "obstacle": "моральный выбор, нарастающая опасность, непредсказуемые партнёры",
      "stakes": "смерть, потеря человечности",
      "rank": "A",
      "type": "serialized",
      "nature": "plot-led",
      "confidence": "solid",
      "devices": ["dramatic_irony"]
    },
    {
      "id": "family",
      "name": "Walt: Family",
      "driver": "walt",
      "goal": "сохранить семью и скрыть правду",
      "obstacle": "рак, давление семьи на лечение, нарастающая ложь",
      "stakes": "распад семьи, разоблачение",
      "rank": "B",
      "type": "serialized",
      "nature": "character-led",
      "confidence": "solid",
      "devices": ["dramatic_irony"]
    },
    {
      "id": "investigation",
      "name": "Hank: Investigation",
      "driver": "hank",
      "goal": "найти производителя нового мета",
      "obstacle": "нет прямых улик, только косвенные следы",
      "stakes": "преступник на свободе, угроза обществу",
      "rank": "C",
      "type": "serialized",
      "nature": "plot-led",
      "confidence": "solid",
      "devices": ["dramatic_irony"]
    },
    {
      "id": "partnership",
      "name": "Jesse: Partnership",
      "driver": "jesse",
      "goal": "выжить как партнёр Уолта в наркобизнесе",
      "obstacle": "некомпетентность, страх, конфликт с Уолтом",
      "stakes": "тюрьма или смерть",
      "rank": "B",
      "type": "serialized",
      "nature": "character-led",
      "confidence": "solid",
      "devices": []
    }
  ]
}
```

### Типы полей

**cast[].**:
- `id`: string — уникальный snake_case идентификатор, используется в `driver` и в Pass 2 `characters`
- `name`: string — полное имя как в credits
- `aliases`: array of strings — варианты имени, встречающиеся в синопсисах

**storylines[].**:
- `id`: string — уникальный snake_case идентификатор (стабильный, не меняется при переименовании)
- `name`: string — display name (см. конвенцию именования)
- `driver`: string — `id` персонажа из cast
- `goal`: string
- `obstacle`: string
- `stakes`: string
- `type`: enum — `"episodic"` | `"serialized"` | `"runner"`
- `rank`: enum — `"A"` | `"B"` | `"C"` | `"runner"` — типичная роль через сезон
- `nature`: enum — `"plot-led"` | `"character-led"`
- `confidence`: enum — `"solid"` | `"partial"` | `"inferred"`
- `devices`: array of strings — нарративные приёмы, характерные для этой линии: `"dramatic_irony"`, `"flashback"`, `"flashforward"`, `"callback"`, `"twist"`, `"unreliable"`. Пустой список если нет.

Язык полей `goal`, `obstacle`, `stakes` — на языке синопсиса.

Поле `span` (в каких эпизодах линия присутствует) вычисляется кодом из результатов Pass 2 — в Pass 1 не указывается.

## Валидация

Валидация выполняется кодом, не LLM. Код проверяет:
- JSON-схема: все обязательные поля, enum-значения
- Каждый `driver` ссылается на существующий `id` в `cast`
- Для procedural/hybrid: ровно одна линия с `type: "episodic"`
- Количество линий в допустимом диапазоне для franchise type

Если код обнаружил ошибку — перезапрос LLM с конкретным указанием что не так.
