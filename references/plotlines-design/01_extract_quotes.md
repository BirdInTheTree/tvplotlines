# Проход 1: Извлечение цитат из книги

Ты читаешь книгу о сценарном мастерстве / структуре ТВ-сериалов / сюжетных линиях.

Твоя задача — извлечь **все значимые цитаты** и сразу разметить их по таксономии. Без интерпретаций, обобщений, пересказа.

## Что извлекать

Конкретные утверждения автора, которые:
- Формулируют правило, принцип или шаблон
- Дают определение термина
- Описывают структуру или компоненты (напр. «эпизод содержит 3 storylines»)
- Разбирают конкретный пример (сериал, фильм) — с указанием какой
- Предупреждают об ошибке или антипаттерне
- Противоречат тому, что говорят другие авторы (это ценно — фиксируй)

## Что НЕ извлекать

- Биографии, благодарности, оглавления, рецензии
- Общие рассуждения без конкретики («сериалы сейчас переживают золотой век»)
- Историю индустрии, если она не влияет на практику сегодня
- Повторы одной мысли — бери самую чёткую формулировку, остальные пропускай

## Формат каждой записи

```json
{
  "source": "{автор: nash / douglas / landau / bennett / pena / venis / sears}",
  "quote": "Точная цитата на языке оригинала. Без сокращений, без пересказа.",
  "page": "p.47 или Chapter 3 или 'Beat Sheet section'",
  "topic": "1-3 слова на английском: о чём цитата (beat sheet, character arc, ABC storylines...)",
  "level": "episode",
  "tag": "beat-sheet",
  "stage": null
}
```

## Таксономия: три поля разметки

### level — масштаб (ЧТО)

| level | описание |
|-------|----------|
| `serial` | Сериал целиком: франшиза, story engine, мир, тон, IP |
| `season` | Сезонная арка, сериализация, A/B/C линии, тема |
| `episode` | Структура эпизода: акты, beat sheet, teaser, пилот |
| `scene` | Сцена, dramatic beat, диалог, подтекст |
| `character` | Арки персонажей, антагонист, эмпатия, ансамбль |
| `script` | Outline, board, формат сценария, драфты |
| `docs` | Logline, pitch, bible, proposal, spec script |
| `industry` | Writers room, development cycle, карьера, showrunning |

### tag — конкретная тема (О ЧЁМ)

Kebab-case. Используй существующие из списка ниже. Если ни один не подходит — создай новый в том же стиле.

```
serial:    franchise-type, story-engine, world-building, tone-genre, ip-adaptation
season:    season-arc, serialized-vs-procedural, abc-storylines, theme, cliffhangers
episode:   act-structure, beat-sheet, cold-open, pilot, m-factor
scene:     dramatic-beat, scene-construction, dialogue-subtext
character: character-arc, antagonist, empathy, ensemble, pov
script:    outline-board, script-format, drafts-polish
docs:      logline, pitch-oral, pitch-design, pitch-meeting, pitch-deck, proposal, series-bible, spec-script
industry:  writers-room, development-cycle, showrunning, breaking-in, marketplace
```

### stage — контекст workflow (ЗАЧЕМ)

| stage | когда ставить |
|-------|---------------|
| `bible` | Цитата явно про сборку bible / документа серии |
| `pitch` | Цитата явно про подготовку к питчу / презентации |
| `writers-room` | Цитата явно про работу в writers room |
| `null` | Общее знание, не привязано к конкретному workflow (большинство цитат) |

## Правила

1. **Цитата = точные слова автора.** Не пересказывай, не сокращай, не переводи. Если фрагмент длинный — допустимо обрезать середину через [...], но начало и конец должны быть точными.

2. **Topic — не интерпретация, а тема.** Пиши что автор обсуждает, не что ты думаешь об этом. «beat sheet» — да. «важность хорошей структуры» — нет.

3. **Одна цитата = одна мысль.** Если автор в одном абзаце говорит про beat sheet И про персонажей — это две записи.

4. **Примеры — отдельно.** Если автор разбирает Breaking Bad — это отдельная запись с topic «example: Breaking Bad». Level и tag ставь по тому, что иллюстрируется.

5. **Не фильтруй по важности.** Извлекай всё, что подходит под критерии. Фильтрация — на следующем этапе.

6. **Страница обязательна.** Если точная страница недоступна — указывай главу или секцию.

7. **Level определяется по масштабу.** Цитата про сцену — `scene`, про целый сериал — `serial`. Не по тому где в книге стоит, а по тому о чём говорит.

8. **Stage = null в большинстве случаев.** Ставь bible/pitch/writers-room только если цитата явно про этот контекст работы.

## Результат

JSON-массив записей. Ожидаемый объём: 80-200 цитат на книгу в зависимости от её длины и плотности.

```json
[
  {
    "source": "nash",
    "quote": "TV shows are more than just stories. They're story engines, story brands.",
    "page": "The Cold Open",
    "topic": "show vs story",
    "level": "serial",
    "tag": "story-engine",
    "stage": null
  },
  {
    "source": "douglas",
    "quote": "Most hour episodes interweave two or three storylines, called the A, B, and C stories.",
    "page": "p.92, Chapter 3",
    "topic": "ABC storylines",
    "level": "season",
    "tag": "abc-storylines",
    "stage": null
  }
]
```
