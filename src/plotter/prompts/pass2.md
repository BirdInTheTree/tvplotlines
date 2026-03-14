# Промпт: Проход 2 — Распределение событий по линиям

> **Самостоятельный документ.** Собран из справочника `storyline-extraction-reference.md`, но подаётся в LLM как есть. При обновлении reference — пересобрать.

## Контракт

- **Вход**: выход Pass 1 (`show`, `season`, `cast`, `storylines`) + синопсис одного эпизода
- **Выход**: JSON с событиями эпизода, привязанными к линиям

## Вход

- **show**, **season**, **franchise_type**, **story_engine**, **format** (из Pass 0, проброшены кодом)
- **cast**: список персонажей с `id` (из Pass 1)
- **storylines**: список линий с `id`, `driver`, `goal` (из Pass 1)
- **synopsis**: синопсис одного эпизода (текст)

## Задача

### Шаг 1: Разбей синопсис на события

Одно событие = одно действие одного персонажа (или группы), меняющее ситуацию. Два действия разных персонажей = два события. Два действия в один момент, второе — немедленное следствие первого = одно событие. Убедись что каждое предложение синопсиса отражено хотя бы в одном событии.

Описания событий должны быть конкретными. Указывай имена персонажей, что именно происходит и к какому драматическому последствию это ведёт. Плохо: «Команда работает над делом.» Хорошо: «Хаус назначает люмбальную пункцию вопреки возражениям Кэмерон, рискуя параличом ради проверки теории о саркоидозе.» Конкретность помогает различать события разных линий.

### Шаг 2: Привяжи каждое событие к линии

### Шаг 3: Определи interactions между линиями

## Правила привязки

1. **По driver**: событие → линия того, чью цель оно продвигает.
2. **Гости → основной каст**: линия принадлежит cast, не гостям.
3. **По цели, не персонажу**: несколько персонажей в сцене → линия того, чью ЦЕЛЬ сцена продвигает.
4. **Double bump — выбирай одну**: событие касается двух линий → привязывай к непосредственной цели, побочно затронутую линию укажи в `also_affects`.
5. **Частота как подсказка**: B-story = 1–2 сцены на акт. Если у линии больше событий чем у A → перепроверь иерархию.

## Функции событий

| function | что делает |
|----------|-----------|
| `setup` | Вводит линию |
| `escalation` | Повышает ставки |
| `turning_point` | Меняет направление |
| `climax` | Кульминация конфликта |
| `resolution` | Разрешение конфликта |
| `cliffhanger` | Обрыв на пике |
| `seed` | Зерно будущей линии |

Для **limited**-сериалов в финальном эпизоде: ожидай `resolution` или `climax` для каждой линии, не `seed` или `cliffhanger`.

## Interactions между линиями

После распределения событий определи связи:

- **Thematic rhyme** — линии исследуют одну тему с разных сторон. Определи тему эпизода по climax/resolution линий.
- **Dramatic irony** — зритель знает то, чего не знает персонаж другой линии.
- **Convergence** — линии сливаются (персонажи/конфликты пересекаются).
- **Meta** — структурный приём поверх линий (subtype: twist-reveal, wraparound, time_jump и др.). Тест: не продвигает цель персонажа, а переосмысляет увиденное для зрителя. Если мета-приём имеет полную Story DNA — это линия, не приём.

**Эмоциональный контрапункт**: если все линии на подъёме или все на спаде — что-то пропущено или неверны function.

## Формат выхода

Ответ — строго JSON, без markdown-обёртки, без комментариев вне JSON.

Weight (`primary` / `background` / `glimpse`) вычисляется кодом из количества событий — НЕ включай в JSON.

```json
{
  "show": "Breaking Bad",
  "season": 1,
  "episode": "S01E03",
  "events": [
    {
      "event": "Уолт и Джесси убирают останки Эмилио",
      "storyline": "empire",
      "function": "escalation",
      "characters": ["walt", "jesse"],
      "also_affects": null
    },
    {
      "event": "Крейзи-8 рассказывает о детстве, Уолт — о раке",
      "storyline": "empire",
      "function": "escalation",
      "characters": ["walt"],
      "also_affects": ["family"]
    },
    {
      "event": "Уолт составляет список «за» и «против» убийства",
      "storyline": "empire",
      "function": "turning_point",
      "characters": ["walt"],
      "also_affects": null
    },
    {
      "event": "Скайлер организует семейную интервенцию",
      "storyline": "family",
      "function": "setup",
      "characters": ["skyler", "walt"],
      "also_affects": null
    },
    {
      "event": "Семья за химию, Уолт хочет отказаться",
      "storyline": "family",
      "function": "escalation",
      "characters": ["walt", "skyler"],
      "also_affects": null
    },
    {
      "event": "Хэнк находит точку варки в пустыне",
      "storyline": "investigation",
      "function": "escalation",
      "characters": ["hank"],
      "also_affects": null
    },
    {
      "event": "DEA находит машину Крейзи-8 с метом",
      "storyline": "investigation",
      "function": "escalation",
      "characters": ["hank"],
      "also_affects": null
    },
    {
      "event": "Индейская девочка приносит маску",
      "storyline": "investigation",
      "function": "seed",
      "characters": ["guest:native_girl"],
      "also_affects": null
    },
    {
      "event": "Уолт решает отпустить Крейзи-8",
      "storyline": "empire",
      "function": "turning_point",
      "characters": ["walt"],
      "also_affects": null
    },
    {
      "event": "Уолт замечает недостающий осколок тарелки",
      "storyline": "empire",
      "function": "turning_point",
      "characters": ["walt"],
      "also_affects": null
    },
    {
      "event": "Уолт удушает Крейзи-8",
      "storyline": "empire",
      "function": "climax",
      "characters": ["walt"],
      "also_affects": null
    },
    {
      "event": "Уолт решает рассказать Скайлер о раке",
      "storyline": "family",
      "function": "turning_point",
      "characters": ["walt"],
      "also_affects": null
    }
  ],
  "summary": {
    "theme": "иллюзия контроля",
    "interactions": [
      {
        "type": "thematic_rhyme",
        "lines": ["empire", "family", "investigation"],
        "description": "все три линии про контроль — над чужой жизнью, своей смертью, законом"
      },
      {
        "type": "dramatic_irony",
        "lines": ["empire", "investigation"],
        "description": "зритель знает что Уолт = Хайзенберг, Хэнк — нет"
      }
    ],
    "patches": []
  }
}
```

### Типы полей

**events[].**:
- `event`: string — одно предложение
- `storyline`: string | null — `id` линии из Pass 1, или `null` если событие не привязывается ни к одной линии (→ патч `ADD_LINE`)
- `function`: enum — `"setup"` | `"escalation"` | `"turning_point"` | `"climax"` | `"resolution"` | `"cliffhanger"` | `"seed"`
- `characters`: array of strings — `id` персонажей из cast. Для гостевых персонажей используй формат `"guest:краткое_имя"` (напр. `"guest:native_girl"`)
- `also_affects`: array of strings | null — `id` побочно затронутых линий

**summary.interactions[].**:
- `type`: enum — `"thematic_rhyme"` | `"dramatic_irony"` | `"convergence"` | `"meta"`
- `lines`: array of strings — `id` линий
- `description`: string
- `subtype`: string | null — только для `"meta"`: `"twist-reveal"`, `"wraparound"`, `"time_jump"` и др.

**summary.patches[].**:
- `action`: enum — `"ADD_LINE"` | `"CHECK_LINE"` | `"SPLIT_LINE"` | `"RERANK"`
- `target`: string — `id` линии (или предлагаемый новый `id`)
- `reason`: string
- `episodes`: array of strings

## Валидация

Валидация выполняется кодом, не LLM. Код проверяет:
- JSON-схема: все обязательные поля, enum-значения
- Каждый `storyline` ссылается на существующий `id` из Pass 1 или равен `null`
- Каждый элемент `characters` ссылается на существующий `id` из cast или имеет префикс `guest:`
- Баланс: A-story > B > C по количеству событий
- `theme` не пустой

Если код обнаружил ошибку — перезапрос LLM с конкретным указанием что не так.

## Патчи к Проходу 1

Pass 2 не перезапускает Pass 1. Собирает патчи — предложения по изменению списка линий. Патчи применяются кодом после обработки всех эпизодов.

| проблема | что делать в эпизоде | патч |
|----------|---------------------|------|
| Событие не привязывается | `storyline: null` | `ADD_LINE` |
| Линия без событий | Ничего | `CHECK_LINE` |
| Линия покрывает разное | Привяжи к текущей | `SPLIT_LINE` |
| C толще A | Отметь | `RERANK` |
