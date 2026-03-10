# Архитектура Plotter

## Принцип: чистая функция

Библиотека — это функция. Всё что нужно — приходит на вход, всё что получилось — уходит на выход. Внутри никаких баз данных, файлов, сессий, скрытого состояния.

Антипаттерн (из mas4bw): граф экстракции внутри себя лезет в SQLite и читает файлы с диска. Это делает код непереносимым и непригодным для библиотеки.

## Входы

```python
result = get_plotlines(
    episodes: list[str],          # обязательно: тексты синопсисов серий
    language: str = "en",         # язык синопсисов ("en", "ru")

    # Контекст сериала — если не задан, определяется автоматически (нулевой этап)
    context: SeriesContext | None = None,

    # Ранее найденные линии — для инкрементальной обработки
    # (пользователь сам решает где хранить: БД, файл, память)
    known_plotlines: list[Plotline] = [],

    # Настройки LLM
    llm_provider: str = "anthropic",  # "anthropic" | "openai"
    model: str | None = None,         # конкретная модель, или дефолт провайдера
)
```

### SeriesContext (определяется автоматически или задаётся вручную)

```python
@dataclass
class SeriesContext:
    story_engine: str       # "новый пациент", "новое дело", "новая сделка"
    franchise_type: str     # "procedural" | "serialized" | "hybrid"
    genre: str              # "drama", "thriller", "comedy"
    format: str | None      # "anthology" | "limited" | "ongoing"
```

### Почему `known_plotlines` — вход, а не БД

В mas4bw шаг 2 графа открывает SQLite чтобы достать "какие арки мы уже нашли раньше". Это создаёт жёсткую зависимость от базы данных.

В Plotter пользователь сам передаёт `known_plotlines` — список того что уже нашлось. Откуда он его взял (из файла, из БД, из памяти) — не наше дело. При первом вызове — пустой список.

## Выходы

```python
@dataclass
class PlotterResult:
    context: SeriesContext          # что определил нулевой этап
    plotlines: list[Plotline]       # найденные сюжетные линии

@dataclass
class Plotline:
    id: str                         # уникальный идентификатор
    label: str                      # "A" | "B" | "C" | "D" ...
    title: str                      # "Марат и Паша — путь в банду"
    type: str                       # "main" | "relationship" | "procedural"
    characters: list[str]           # ["Марат", "Паша", "Вова"]
    episodes: dict[int, str]        # {1: "завязка", 3: "конфликт", 5: "кульминация"}
    description: str                # краткое описание линии
```

## Этапы пайплайна

Детальная спецификация алгоритма — в `md/storyline-extraction-reference.md`. Там теория из книг, правила, worked examples (House, Breaking Bad, This Is Us). Ниже — краткая схема.

```
Синопсисы → [0a. Franchise type] → [0b. Story engine] → [Проход 1: линии] → [Проход 2: события по линиям] → Plotlines
```

**Шаг 0a. Franchise type** (procedural / serialized / hybrid / ensemble)
- Определяет СТРУКТУРУ линий
- Procedural → A закрытая (case-of-week), B/C сериализованные
- Serialized → все линии сквозные
- Ensemble → несколько равноправных линий по персонажам

**Шаг 0b. Story engine**
- Определяет КАКИЕ линии искать
- Case-of-week → линия расследования/пациента
- Transformation machine → линия трансформации героя

(1 LLM-вызов на оба, пропускается если context задан вручную)

**Проход 1: Извлечение линий** (вход: ВСЕ синопсисы сезона)
- LLM читает все синопсисы целиком
- Для каждой линии: name, driver, goal, obstacle, stakes, type, nature, span
- Валидация: Story DNA (hero + goal + obstacle + stakes), тест логлайна, соответствие franchise type
- Негативные примеры: что НЕ является линией (см. reference)

**Проход 2: Распределение событий** (вход: один эпизод + список линий из Прохода 1)
- Для каждого события: storyline, function, characters, double_bump
- Правила привязки: по персонажу-драйверу, по цели, по каузальной связи
- Валидация: полное покрытие синопсиса, прогресс линий, каузальность, баланс A>B>C

**Итерация:** если Проход 2 находит проблемы → назад в Проход 1 (пропущена линия, лишняя линия, слишком крупно/мелко)

## Чего внутри НЕ будет

- ❌ Базы данных (SQLite, ChromaDB)
- ❌ Чтения/записи файлов
- ❌ Веб-сервера, API
- ❌ Скрытого состояния между вызовами
- ❌ NLP-предобработки (spaCy, Natasha) — синопсисы уже чистые
