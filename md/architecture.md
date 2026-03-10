# Архитектура Plotter

## Принцип: чистая функция

Библиотека — это функция. Всё что нужно — приходит на вход, всё что получилось — уходит на выход. Внутри никаких баз данных, файлов, сессий, скрытого состояния.

Антипаттерн (из mas4bw): граф экстракции внутри себя лезет в SQLite и читает файлы с диска. Это делает код непереносимым и непригодным для библиотеки.

## Входы

```python
result = get_plotlines(
    show: str,                        # название шоу
    season: int,                      # номер сезона
    episodes: list[str],              # синопсисы ВСЕХ серий сезона (на любом языке)

    # Контекст сериала — если не задан, определяется автоматически (Pass 0)
    context: SeriesContext | None = None,

    # Настройки LLM
    llm_provider: str = "anthropic",  # "anthropic" | "openai"
    model: str | None = None,         # конкретная модель, или дефолт провайдера
)
```

### SeriesContext (определяется автоматически или задаётся вручную)

```python
@dataclass
class SeriesContext:
    franchise_type: str     # "procedural" | "serial" | "hybrid" | "ensemble"
    story_engine: str       # одно предложение — механизм генерации историй
    genre: str              # "drama", "thriller", "comedy"
    format: str | None      # "anthology" | "limited" | "ongoing"
```

### Состояние между эпизодами — внутри, не снаружи

В mas4bw пользователь должен был хранить найденные арки в SQLite и передавать между вызовами. В Plotter — подаёшь весь сезон, функция сама проходит эпизод за эпизодом и накапливает линии в памяти. Пользователь об этом не думает.

## Выходы

Структуры данных соответствуют выходу промптов Pass 1 и Pass 2. Промпты — источник истины, архитектура отражает их.

```python
@dataclass
class PlotterResult:
    context: SeriesContext                # что определил Pass 0
    cast: list[CastMember]               # основной каст (из Pass 1)
    plotlines: list[Plotline]             # найденные сюжетные линии (из Pass 1)
    episodes: list[EpisodeBreakdown]      # поэпизодная разбивка (из Pass 2)

@dataclass
class CastMember:
    id: str                         # snake_case идентификатор: "walt", "jesse"
    name: str                       # полное имя: "Walter White"
    aliases: list[str]              # варианты в синопсисах: ["Walt", "Heisenberg"]

@dataclass
class Plotline:
    id: str                         # snake_case идентификатор: "empire", "family"
    name: str                       # display name по цели: "Empire", "Investigation"
    driver: str                     # id персонажа из cast
    goal: str                       # чего хочет драйвер
    obstacle: str                   # что мешает
    stakes: str                     # что на кону
    type: str                       # "episodic" | "serialized" | "runner"
    rank: str                       # "A" | "B" | "C" | "runner" — типичная роль через сезон
    nature: str                     # "plot-led" | "character-led"
    confidence: str                 # "solid" | "partial" | "inferred"
    span: list[str]                 # вычисляется кодом из Pass 2: ["S01E01", "S01E03"]

@dataclass
class Event:
    event: str                      # что произошло (одно предложение)
    storyline: str | None           # id линии, или None (→ патч ADD_LINE)
    function: str                   # "setup" | "escalation" | "turning_point" | "climax" | "resolution" | "cliffhanger" | "seed"
    characters: list[str]           # id персонажей из cast; гости: "guest:краткое_имя"
    also_affects: list[str] | None  # id побочно затронутых линий

@dataclass
class Interaction:
    type: str                       # "thematic_rhyme" | "dramatic_irony" | "convergence" | "meta"
    lines: list[str]                # id линий
    description: str                # что происходит (одно предложение)
    subtype: str | None = None      # для meta: "twist-reveal", "wraparound", "time_jump"

@dataclass
class Patch:
    action: str                     # "ADD_LINE" | "CHECK_LINE" | "SPLIT_LINE" | "RERANK"
    target: str                     # id линии (или предлагаемый новый id)
    reason: str                     # что обнаружено
    episodes: list[str]             # в каких эпизодах проблема

@dataclass
class EpisodeBreakdown:
    episode: str                    # "S01E03"
    events: list[Event]             # события эпизода
    theme: str                      # тема эпизода (одно предложение)
    interactions: list[Interaction]
    patches: list[Patch]            # предложения по изменению списка линий
```

### Вычисляемые поля (код, не LLM)

- **`Plotline.span`** — агрегируется из результатов Pass 2 (в каких эпизодах есть события линии)
- **Weight** (`primary` / `background` / `glimpse`) — вычисляется из количества событий линии в эпизоде

## Этапы пайплайна

Детальная спецификация алгоритма — в `md/storyline-extraction-reference.md`. Там теория из книг, правила, worked examples (House, Breaking Bad, This Is Us). Ниже — краткая схема.

```
Синопсисы → [Pass 0: контекст] → [Pass 1: линии + каст] → [Pass 2: события по эпизодам] → [Пост-обработка: span, weight, патчи] → PlotterResult
```

**Pass 0: Определение контекста** (отдельный промпт, пропускается если context задан вручную)
- Вход: описание шоу (если есть) + 2–3 первых синопсиса
- Выход: franchise_type + story_engine + обоснование
- Franchise type определяет СТРУКТУРУ линий:
  - Procedural → A закрытая (case-of-week), B/C сериализованные
  - Serial → все линии сквозные
  - Hybrid → A закрытая + B/C открытые
  - Ensemble → несколько равноправных линий по персонажам
- Story engine: модель выбирает из шаблонов по franchise type и заполняет слоты
- Человек подтверждает или правит результат перед запуском Pass 1

**Pass 1: Извлечение линий и каста** (вход: все синопсисы + контекст из Pass 0)
- LLM читает все синопсисы целиком
- Выход: cast (id, name, aliases) + storylines (id, name, driver, goal, obstacle, stakes, type, rank, nature, confidence)
- Span НЕ определяется — вычисляется кодом из Pass 2
- Валидация кодом: JSON-схема, driver → cast, episodic-линия для procedural/hybrid, количество линий

**Pass 2: Распределение событий** (вход: один эпизод + cast + storylines из Pass 1)
- Запускается поэпизодно
- Выход: events (storyline, function, characters, also_affects) + summary (theme, interactions) + patches
- Валидация кодом: storyline/characters → id из Pass 1, баланс A>B>C

**Пост-обработка** (код, не LLM):
- Агрегация span из всех Pass 2 (в каких эпизодах линия имеет события)
- Вычисление weight (primary/background/glimpse) из количества событий
- Сбор и анализ патчей: ADD_LINE, CHECK_LINE, SPLIT_LINE, RERANK
- При необходимости — перезапуск Pass 1 с учётом патчей

## Структура LLM-вызовов

Каждый вызов состоит из двух частей:
- **System prompt** (стабильный) — текст промпт-файла целиком. Правила, определения, формат выхода. Не меняется между вызовами одного прохода.
- **User message** (динамический) — конкретные данные для этого вызова.

```
Pass 0:  system = prompt-pass0-detect-context.md
         user   = {show, season, description, sample_synopses: первые 2–3}

Pass 1:  system = prompt-pass1-extract-storylines.md
         user   = {show, season, franchise_type, story_engine, synopses: все}

Pass 2:  system = prompt-pass2-assign-events.md          ← КЭШИРУЕТСЯ
         user   = {show, season, franchise_type,          ← меняется только
                   story_engine, cast, storylines,            synopsis
                   synopsis: один эпизод}
```

### Оптимизации

**Prompt caching (Anthropic):** system prompt кэшируется на стороне API. Платишь за токены system prompt один раз, дальше переиспользуешь. Критично для Pass 2 — один и тот же промпт для N эпизодов.

**Batching (Anthropic Message Batches API):** вызовы Pass 2 для разных эпизодов независимы. Можно отправить пачкой — 50% скидка, без давления на rate limit.

**Минимизация user message:** в Pass 2 передаём cast и storylines целиком (они нужны для привязки), но только один synopsis. Это дешевле чем передавать контекст всего сезона в каждый вызов.

## Два слоя: библиотека и приложение

```
┌─────────────────────────────────────────────┐
│  Приложение (не open source, твой продукт)  │
│                                             │
│  Интерфейс → редактирование → БД → экспорт │
│         │                     ▲              │
│         ▼                     │              │
│   get_plotlines()  →  результат              │
│                                             │
│  ┌─────────────────────────────────────┐    │
│  │  Библиотека (open source, pip)      │    │
│  │                                     │    │
│  │  синопсисы → обработка → результат  │    │
│  │  (без БД, без файлов, без UI)       │    │
│  └─────────────────────────────────────┘    │
└─────────────────────────────────────────────┘
```

**Библиотека** — только вычисление. Как калькулятор: подал числа, получил ответ. Не знает ни про файлы, ни про интерфейсы.

**Приложение** — как Excel: показывает результат, хранит, даёт редактировать. Вызывает библиотеку внутри. Это то, чем ты пользуешься сейчас в mas4bw (интерфейс, БД, дашборд).

Open source = только библиотека. Приложение = твой продукт.

## Утилиты

**`plotter prepare`** — подготовка входных данных. Принимает PDF/TXT с синопсисами, выдаёт `list[str]` (один элемент = один эпизод).

**`plotter lookup`** — подтягивает метаданные шоу из TMDB/IMDb по названию: жанр, формат (ongoing/limited/anthology), описание. Результат можно передать в `SeriesContext` или использовать как вход Pass 0 (поле `description`).

Утилиты не часть основного пайплайна, но поставляются с пакетом.

## Чего внутри библиотеки НЕ будет

- ❌ Базы данных (SQLite, ChromaDB)
- ❌ Чтения/записи файлов
- ❌ Веб-сервера, API
- ❌ Интерфейса, дашборда
- ❌ Скрытого состояния между вызовами
- ❌ NLP-предобработки (spaCy, Natasha) — синопсисы уже чистые
