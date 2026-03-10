# Plotter — контекст проекта

## Что это

Plotter — инструмент для извлечения и анализа сюжетных линий из синопсисов сериалов. Переписывается с нуля на основе идей из статьи Balestri & Pescatore (ICAART 2025), но с собственной теоретической базой и классификацией.

## Предыстория

Начался как форк mas4bw (Multi-Agent System for AI-Assisted Extraction of Narrative Arcs). Форк расширил оригинал: русский язык, синопсис-пайплайн, мульти-LLM, 11+ сериалов. Но лицензия оригинала (CC BY-NC-ND) запрещает производные работы, поэтому — переписываем с нуля.

## Ключевое отличие от оригинала

Оригинал: эмпирический подход (попробовали на Grey's Anatomy → вроде работает, 9 фиксированных шагов, академические типы арок anthology/soap/genre).

Plotter: **знания из книг → формальная модель → инструкции для ИИ**. Классификация A/B/C storylines из индустриальной практики. Количество шагов определяется теорией, а не экспериментом.

## Что своё

- A/B/C классификация сюжетных линий (вместо anthology/soap/genre)
- Procedural / serialized / hybrid типология
- Синопсис-пайплайн (синопсисы как основной вход, без тяжёлой NLP-обработки)
- Русский язык (NER через Natasha)
- Мульти-LLM (OpenAI, Anthropic, Azure)
- База знаний из ~20 книг по сериальной структуре
- Формальные модели из books2series (предикаты W/B/I/Ψ, каузальные связи, kernel/satellite)

## Что берём как идею (из статьи, не код)

- Мультиагентный подход (несколько LLM-вызовов с разными ролями)
- Дедупликация через векторное сходство
- Верификация результатов отдельным шагом

## Целевой интерфейс

```python
from plotter import extract_storylines

storylines = extract_storylines(
    episodes=["синопсис серии 1", "синопсис серии 2", ...],
    language="ru",
    genre="drama",
)

for s in storylines:
    print(s.label)       # "A" / "B" / "C"
    print(s.title)       # "Марат и Паша — путь в банду"
    print(s.characters)  # ["Марат", "Паша", "Вова"]
    print(s.episodes)    # {1: "завязка", 3: "конфликт", 5: "кульминация"}
```

## Связанные проекты

- **mas4bw** (`/Projects/misc/mas4bw`) — оригинальный форк, reference implementation
- **books2series** (`/Projects/books2series`) — пайплайн книга→события, формальные модели (W/B/I/Ψ, каузальные связи), directed extraction с storyline_id
- **how2pitch** (`/Projects/how2pitch`) — база знаний по питчу, plotlines knowledge base (строится)

## Структура проекта

```
Plotter/
├── CONTEXT.md              ← этот файл
├── CLAUDE.md               ← инструкции для Claude
├── md/                     ← планы, аудиты, стратегия
│   ├── inventory.md        ← инвентаризация: своё/чужое/теория/технология
│   ├── open-source-strategy.md
│   └── mas4bw-library-audit.md
├── references/             ← релевантные документы из других проектов
│   ├── plotlines-design/   ← дизайн базы знаний по сюжетным линиям
│   ├── plotlines-quotes/   ← цитаты из книг про структуру
│   ├── structure_sketch.yaml ← формат storyline из books2series
│   └── ...
└── src/                    ← код (пока пусто)
```

## Открытые вопросы

- Сколько шагов в новом пайплайне? (определится из книг)
- Монорепо с books2series/how2pitch или отдельный пакет?
- Название пакета: plotter? storylines? narrative-kit?
- Писать авторам Balestri & Pescatore (для контакта, не для разрешения)
