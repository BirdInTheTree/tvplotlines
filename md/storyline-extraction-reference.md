# Справочник: извлечение сюжетных линий из синопсисов

Материал для построения промпта тула, который:
1. Извлекает сюжетные линии из синопсисов серий
2. Расписывает события каждой серии по линиям

Собран из базы знаний (pitch_bible + plotlines). Помечен тегами вопросов:
- `[DEF]` — что такое линия, критерии
- `[ARC]` — связь линии и арки
- `[MUST]` — что обязательно должно быть в линии
- `[ASSIGN]` — как отнести событие к линии
- `[TYPE]` — типы линий
- `[INTERACT]` — как линии взаимодействуют

## Предварительные шаги (перед извлечением линий)

### Шаг 0a: Определить тип франшизы

Тип франшизы предопределяет структуру линий:
- **Procedural** → A-story закрытая (case-of-week), B/C сериализованные
- **Serial** → все линии сквозные, арки на весь сезон
- **Hybrid** → A закрытая + B/C открытые
- **Ensemble** → несколько равноправных линий по персонажам

> "There are five main series types today: Procedural (closed-ended), Serial (open-ended), Serial-Procedural Hybrid, Sitcom and Mini-Series." — Oberg, p.46

### Шаг 0b: Определить story engine

Story engine = механизм генерации историй. Знание его помогает понять КАКИЕ линии искать.

> "Every TV series needs a story engine – a built-in mechanism that will generate stories for the run of the series." — Landau, p.317
> "A TV series is a transformation machine designed to test the same character flaw over and over." — Nash, p.12

---

## [DEF] Что такое сюжетная линия — критерии

### Обязательные компоненты (Story DNA)

> "Story DNA has four parts: Hero, Goal, Obstacle, Stakes." — Nash, p.34 `[DEF][MUST]`

Если у «линии» нет своего героя, цели, препятствия и ставок — это не линия, это событие.

### Структура

> "In a multi-stranded narrative, each strand usually has its own dramatic three-act structure." — Oberg, p.60 `[DEF][MUST]`

Каждая линия = мини-история со своей завязкой, конфликтом, развязкой.

### Привязка к персонажу

> "Each story is usually 'driven by' one character in the main cast." — Douglas, p.151 `[DEF][ASSIGN]`

> "The point isn't what you call a story but how well you attach it to the drive of a continuing character." — Douglas, p.132 `[DEF]`

### Конфликт обязателен

> "I suggest that you create real dramatic log lines. That way, you'll be sure your stories have conflict — that they're actually stories, not just situations." — Douglas, p.148 `[DEF][MUST]`

### Движение вперёд обязательно

> "Stories are like sharks; if they don't move forward, they die." — Venis, p.84-85 `[MUST]`

### Каузальная цепь

> "Causality is essential in storytelling. Events should happen as a result of what happened before, not by coincidence." — Oberg, p.148 `[MUST]`

---

## [ARC] Связь линии и арки

> "The arcs of a TV series are the story lines that continue across episodes." — Venis, p.62 `[ARC]`

Арка = линия, которая тянется через несколько эпизодов. Эпизодная линия = линия, которая закрывается внутри эпизода.

> "Some showrunners begin with a chart of story arcs for the whole season. [...] they assign each character a color-coded marker and track the five-or-so main roles from Episode 1 to 22 in horizontal lines. After all arcs are complete, they slice vertically." — Douglas, p.96-97 `[ARC]`

Горизонтальные линии = арки персонажей через сезон. Вертикальный срез = эпизод.

> "Every episode, the character steps up to the line of change... and then steps back." — Nash, p.11 `[ARC]`

В ТВ арки прогрессируют инкрементально, не завершаются за один эпизод.

---

## [ASSIGN] Как отнести событие к линии

### Правило 1: По персонажу-драйверу

> "The A story usually belongs to the series hero. The B story is the second-biggest story." — Nash, p.88 `[ASSIGN]`

> "Notice in each case I've stated the stories as issues for main cast, not the guest cast, though the guests are bringing the inciting incidents." — Douglas, p.148 `[ASSIGN]`

Событие принадлежит линии того персонажа из основного каста, чью цель/проблему оно продвигает.

### Правило 2: По цели и ставкам

> "Today, most writers simply breakdown the main storylines (A, B, C) around their respective goals / what's at stake in each strand." — Oberg, p.484 `[ASSIGN]`

### Правило 3: Double bump — исключение

> "Double bump — when you combine two problems into one scene, it has twice the impact. One event affects two stories simultaneously." — Nash, p.105 `[ASSIGN][INTERACT]`

Одно событие МОЖЕТ принадлежать двум линиям одновременно.

### Правило 4: Частота появления

> "Usually, a B story, and especially a C story, will only have one scene per act. At most, two." — Venis `[ASSIGN][TYPE]`

---

## [TYPE] Типы линий

### По иерархии (A/B/C)

> "The A-Story is the main storyline, usually driven by the protagonist. The B-Story is secondary, often character-led. The C-Story is third, often lighter in tone." — Oberg, p.58 `[TYPE]`

> "B Stories are theme Sherpas. It's their job to carry the theme and directly address the hero's need." — Nash, Ch.5 `[TYPE]`

### По длительности

- **Эпизодная** (закрытая): завершается внутри эпизода
- **Сквозная** (сериализованная): тянется через несколько эпизодов/весь сезон
- **Runner**: маленькая повторяющаяся линия, может никогда не разрешиться

> "Also, many shows often employ runners, or story threads. These are small running story lines or jokes that may never truly resolve." — Venis, p.115 `[TYPE]`

### По характеру конфликта

- **Plot-led**: внешняя цель vs антагонист
- **Character-led**: внутренний конфликт, протагонист = собственный антагонист

> "In a character-led story, the protagonist is the antagonist. The main problem lies within the protagonist." — Oberg, p.191 `[TYPE]`

### Особые типы и как их отличать

#### Runner vs C-story

| | C-story | Runner |
|---|---|---|
| Story DNA | Полная: hero + goal + obstacle + stakes | Неполная: hero + ситуация, но нет obstacle или resolution |
| Структура | Завязка → конфликт → развязка | Повторяющийся мотив без развязки |
| Экранное время | 1-2 сцены на акт, стабильно | Появляется нерегулярно, по 1 сцене |
| Разрешение | Закрывается в эпизоде (или в сезоне) | Может не разрешиться никогда |
| Пример | «Хэнк расследует Хайзенберга» | «Хэнк собирает минералы» |

> "Also, many shows often employ runners, or story threads. These are small running story lines or jokes that may never truly resolve." — Venis, p.115 `[TYPE]`

**Тест:** если можно написать логлайн с конфликтом — это C-story. Если логлайн выходит описательным («Хэнк увлекается минералами») — это runner.

#### Seed

Seed = событие или мини-линия, которая в текущем эпизоде выглядит как runner или фон, но в будущих эпизодах вырастает в полноценную A/B-story.

> "Among variations, you may find a 'C' story in one episode is a seed beginning a major arc in subsequent episodes." — Douglas, p.111 `[TYPE]`

**Как распознать:** seed видно только ретроспективно (из Прохода 1, когда LLM читает все синопсисы). Если `mentioned`-событие в эпизоде 3 становится `confirmed`-линией в эпизоде 7 — пометь эпизод 3 как seed.

#### Wraparound

Появляется в начале и конце эпизода, но не в середине. Часто используется для тематического обрамления.

**Тест:** если линия появляется только в тизере и финальной сцене — это wraparound.

---

## [INTERACT] Как линии взаимодействуют

### The Blend

> "The Blend is the process of weaving multiple story threads into a single beat sheet." — Nash, p.104 `[INTERACT]`

> "To do The Blend: beat out the A story first. Then beat out the B story. Then lay them side by side and interleave them." — Nash, p.104 `[INTERACT]`

### Тематические рифмы

> "When blending multiple threads, look for thematic echoes. The A story's Midpoint and the B story's Midpoint should rhyme." — Nash, p.151 `[INTERACT]`

> "Theme is a central idea expressed through action. In episodic television, theme is the glue that holds multiple, and sometimes divergent, storylines together." — Landau, p.245 `[INTERACT]`

### Story tentacles

> "Story tentacles are the ripple effects — the emotional and narrative consequences that extend from a single story event and touch every character on the canvas." — Landau, p.100 `[INTERACT]`

### Эмоциональный контрапункт

> "In an ensemble, every character can't be at the same emotional place at the same time. You stagger them. When one is up, another is down." — Nash, p.89 `[INTERACT]`

### Информационная асимметрия

> "There is dramatic irony between strands (the audience knows Will is in the Upside Down before the characters do)." — Oberg, p.132 `[INTERACT]`

### Convergence

> "Subplots can dovetail into the main plot." — Venis `[INTERACT]`

---

## Эвристика гранулярности

Главный вопрос: «Уолт готовит мет, ссорится со Скайлер, Хэнк расследует» — это 3 линии или 2?

**Ключ — не персонаж, а ЦЕЛЬ.** Один персонаж может вести несколько линий, если у него несколько целей:
- Уолт + цель «построить империю» = линия Power
- Уолт + цель «сохранить семью» = линия Family
- Хэнк + цель «поймать Хайзенберга» = линия Investigation

Ссора со Скайлер — не отдельная линия, а событие внутри линии Family (или линии Скайлер, если у неё своя цель).

### Правила разделения

Два события принадлежат **ОДНОЙ линии**, если:
1. Один и тот же персонаж-драйвер
2. Одна и та же цель
3. Каузальная связь между ними

Два события — **РАЗНЫЕ линии**, если:
1. Разные персонажи-драйверы, ИЛИ
2. Один персонаж, но разные цели (empire vs family), ИЛИ
3. Нет каузальной связи

### Тест логлайна

> "Create real dramatic log lines. That way, you'll be sure your stories have conflict — that they're actually stories, not just situations." — Douglas, p.148

Если для предполагаемой линии нельзя написать логлайн (герой + цель + препятствие) — это не линия, это событие внутри другой линии.

### Негативные примеры: что НЕ является линией

LLM склонны к over-extraction — создают линии из всего что движется. Вот что линией НЕ является:

| пример | почему не линия | что это на самом деле |
|--------|----------------|----------------------|
| «Джон обедает» | Нет цели, нет конфликта | Событие-фон, не привязано к Story DNA |
| «Все герои идут на вечеринку» | Нет персонажа-драйвера, нет ставок | Сеттинг — место действия для других линий |
| «Джон грустит» | Нет цели, нет препятствия | Эмоциональное состояние, не линия. Может быть последствием события в другой линии |
| «Линия дружбы Джона и Майка» | Нет конфликта, нет ставок | Отношения — это контекст, не линия. Линией станет когда появится конфликт: «Джон скрывает от Майка правду» |
| «Расследование убийства» (в процедурале, эпизод 5) | Это не отдельная линия — это инстанциация franchise engine | Часть A-story данного эпизода. Линия = franchise engine, а конкретное дело = её эпизодное наполнение |
| «Джон покупает кофе, потом едет на работу, потом разговаривает с боссом» | Три события, но одна цель (рабочий день) | Одна линия (если есть цель/конфликт) или просто фон (если нет) |

### Правило: сомневаешься — НЕ создавай линию

Лучше пропустить слабую линию и пометить события как `mentioned` внутри другой линии, чем создать фантомную линию без Story DNA.

> "If a scene doesn't have conflict and emotional change, it's not a scene. It's a transition." — Nash, p.231

То же для линий: если нет конфликта и изменения — это не линия, это фон.

---

## Работа с неполными синопсисами

Реальные синопсисы часто описывают A-story подробно, а B/C — одним предложением. Это не баг, а данные.

### Кросс-эпизодное восполнение

Проход 1 читает ВСЕ синопсисы сезона. Линия Скайлер может быть одним предложением в эпизоде 3, но подробной в эпизоде 7. Story DNA восстанавливается из совокупности упоминаний, а не из одного эпизода.

### Три уровня уверенности

Для каждой линии и каждого события — уровень confidence:

| уровень | значение | когда ставить |
|---------|----------|---------------|
| `confirmed` | Есть полная Story DNA (hero + goal + obstacle + stakes) | Линия подробно описана хотя бы в одном эпизоде |
| `partial` | Есть герой и цель, но obstacle/stakes не ясны | Линия упоминается в нескольких эпизодах, но без деталей |
| `mentioned` | Упомянуто без контекста, Story DNA не выводится | Одно предложение, нет данных для выводов |

**Правило: не выдумывай — помечай.** Лучше честный `partial` чем галлюцинированные ставки.

### Асимметрия как сигнал

Если A-story описана в 5 предложениях, а B в одном — это подсказка о весе линии в эпизоде. Поле `weight` фиксирует это:

| weight | значение |
|--------|----------|
| `primary` | Линия занимает основное пространство синопсиса |
| `background` | Линия упомянута, но не в фокусе |
| `mentioned` | Одно упоминание без развития |

Это пригодится для визуализации и для понимания ритма линии через сезон.

---

## Архитектура промпта: два прохода

### Вход
- Синопсисы серий (текст)
- Тип франшизы (procedural / serial / hybrid / ensemble) — **определяется в Шаге 0a**
- Story engine (одно предложение) — **определяется в Шаге 0b**

Тип франшизы предопределяет структуру линий:
- **Procedural** → A-story закрытая (case-of-week), B/C сериализованные
- **Serial** → все линии сквозные, арки на весь сезон
- **Hybrid** → A закрытая + B/C открытые
- **Ensemble** → несколько равноправных линий по персонажам

### Проход 1: Извлечение линий (вход: ВСЕ синопсисы сезона)

LLM читает все синопсисы целиком, чтобы видеть сквозные линии и runners.

Для каждой линии определить:
- **name**: короткое имя линии
- **driver**: персонаж-драйвер из основного каста
- **goal**: цель персонажа
- **obstacle**: главное препятствие
- **stakes**: что произойдёт если цель не достигнута
- **type**: episodic (закрытая в эпизоде) | serialized (сквозная) | runner (мелкая повторяющаяся)
- **nature**: plot-led (внешний конфликт) | character-led (внутренний конфликт)
- **span**: в каких эпизодах присутствует (e.g. S01E01-S01E10)

Валидация прохода 1:
- У каждой линии есть Story DNA (hero, goal, obstacle, stakes)?
- Можно ли написать логлайн для линии? Если нет — это не линия.
- Не слишком ли крупно? (A+B в одной — разбей по целям)
- Не слишком ли мелко? (одно событие — не линия, это событие в другой линии)
- Количество линий соответствует franchise-type? (procedural: 2-3, ensemble: 4-6)

### Проход 2: Распределение событий (вход: один эпизод + список линий)

Для каждого события из синопсиса:
- **event**: что произошло (одно предложение)
- **storyline**: к какой линии относится (по driver + goal)
- **double_bump**: если событие продвигает две линии — указать обе
- **function**: setup | escalation | turning_point | climax | resolution | cliffhanger
- **characters**: кто участвует

Правила привязки:
1. По персонажу-драйверу: событие принадлежит линии того, чью цель оно продвигает
2. Гости приносят inciting incidents, но линия принадлежит основному касту
3. Одно событие может быть в двух линиях (double bump) — помечай обе
4. Если событие не привязывается ни к одной линии → вернуться в Проход 1 и проверить: пропущена линия?

Валидация прохода 2:
1. **Полное покрытие синопсиса.** Каждое предложение/событие синопсиса должно быть отнесено хотя бы к одной линии. Перечитай синопсис и проверь: не пропущено ли что-то? Если событие не привязано — либо пропущена линия (→ вернуться в Проход 1), либо это фон (→ пометь как `background` с пояснением почему не линия).
2. **Прогресс линий.** Каждая линия из Прохода 1 продвигается хотя бы раз за эпизод? Если нет: это runner, или линия отсутствует в этом эпизоде (ок для serialized), или линия определена слишком мелко.
3. **Каузальность.** Есть каузальная связь между событиями одной линии? Если события одной линии не связаны причинно — возможно это разные линии.
4. **Баланс.** A-story должна иметь больше событий чем B, B больше чем C. Если C толще A — перепроверь иерархию.

### Итерация между проходами

Если Проход 2 обнаруживает проблемы → вернуться в Проход 1:
- Нашлись события без линии → возможно пропущена линия, добавить
- Линия есть, но ни одного события → линия лишняя, убрать
- Одна линия покрывает слишком разные события → разбить по целям

---

## Worked examples

### Пример 1: Procedural (House M.D.)

**Franchise type:** procedural (case-of-week)
**Story engine:** каждую неделю загадочный диагноз проверяет гениальность и человечность Хауса

**Синопсис (вымышленный эпизод):**
> Пациентка — учительница — теряет сознание на уроке. Хаус берёт случай, потому что симптомы не складываются. Команда предлагает волчанку, Хаус отвергает. Кэмерон сочувствует пациентке. Форман проводит обыск дома, находит плесень. Лечение от плесени не помогает. Кадди требует от Хауса извиниться перед донором больницы, которого он оскорбил. Хаус отказывается. Пациентке хуже. Хаус замечает, что она чешет ногу — это подсказка. Диагноз: отравление таллием. Уилсон уговаривает Хауса извиниться, тот нехотя соглашается.

**Проход 1 — линии:**

| name | driver | goal | obstacle | stakes | type | nature |
|------|--------|------|----------|--------|------|--------|
| Case: отравление | House | поставить диагноз | симптомы не складываются | пациентка умрёт | episodic | plot-led |
| Донор | House | избежать извинения | Cuddy давит, Wilson уговаривает | больница потеряет финансирование | episodic | character-led |

**Что НЕ линия:**
- «Кэмерон сочувствует пациентке» — эмоциональная реакция, нет своей цели → событие внутри линии Case
- «Форман проводит обыск» — действие внутри линии Case (служит цели Хауса — диагноз)

**Проход 2 — события:**

| event | storyline | function |
|-------|-----------|----------|
| Учительница теряет сознание | Case | setup |
| Хаус берёт случай | Case | setup |
| Команда предлагает волчанку, Хаус отвергает | Case | escalation |
| Кэмерон сочувствует пациентке | Case | background |
| Форман находит плесень | Case | turning_point |
| Лечение не помогает | Case | escalation |
| Кадди требует извинения | Донор | setup |
| Хаус отказывается | Донор | escalation |
| Пациентке хуже | Case | escalation |
| Хаус замечает подсказку | Case | turning_point |
| Диагноз: отравление таллием | Case | resolution |
| Уилсон уговаривает, Хаус соглашается | Донор | resolution |

---

### Пример 2: Serial (Breaking Bad S1)

**Franchise type:** serial
**Story engine:** школьный учитель строит наркоимперию, проверяя как далеко он готов зайти

**Синопсис (S01E03, упрощённый):**
> Уолт и Джесси должны избавиться от тела Крейзи-8, запертого в подвале. Уолт составляет список «за» и «против» — убивать или отпустить. Скайлер беспокоится о странном поведении Уолта, организует интервенцию по поводу его лечения рака. Хэнк показывает семье видео с работы — захват наркоточки. Уолт решает отпустить Крейзи-8, но обнаруживает, что тот спрятал осколок тарелки. Уолт убивает его.

**Проход 1 — линии:**

| name | driver | goal | obstacle | stakes | type | nature |
|------|--------|------|----------|--------|------|--------|
| Empire | Walt | построить наркобизнес | конкуренты, закон, собственная мораль | смерть / тюрьма | serialized | plot-led |
| Family | Walt | сохранить семью, скрыть правду | Скайлер замечает странности | потеря семьи | serialized | character-led |
| Investigation | Hank | поймать производителя мета | нет улик | преступники на свободе | serialized | plot-led |

**Что НЕ линия:**
- «Интервенция по поводу рака» — событие внутри линии Family (Скайлер пытается понять что с Уолтом)
- «Хэнк показывает видео» — seed: пока фон, но усиливает линию Investigation (и иронию — Уолт за столом)

**Проход 2 — события:**

| event | storyline | function |
|-------|-----------|----------|
| Уолт и Джесси с телом в подвале | Empire | escalation |
| Уолт составляет список за/против | Empire | escalation (double bump: character-led момент внутри plot-led линии) |
| Скайлер беспокоится | Family | escalation |
| Интервенция по лечению рака | Family | turning_point |
| Хэнк показывает видео | Investigation | seed / background |
| Уолт решает отпустить | Empire | turning_point |
| Обнаруживает осколок | Empire | turning_point |
| Уолт убивает Крейзи-8 | Empire | climax |

---

### Пример 3: Ensemble (This Is Us S1)

**Franchise type:** ensemble
**Story engine:** одна семья в двух временных линиях — прошлое объясняет настоящее, проверяя связь между поколениями

**Синопсис (вымышленный эпизод, упрощённый):**
> Кевин репетирует новую пьесу, но не может заплакать на сцене — режиссёр грозит заменой. Кейт записывается на курсы пения, но паникует перед первым занятием. Рэндалл узнаёт, что биологический отец болен, и решает его навестить — Бет против. В флэшбеке: маленький Кевин ревнует, что Джек проводит всё время с Рэндаллом. Джек берёт Кевина на стройку и говорит: «ты особенный по-своему».

**Проход 1 — линии:**

| name | driver | goal | obstacle | stakes | type | nature |
|------|--------|------|----------|--------|------|--------|
| Kevin: актёр | Kevin | доказать себя как серьёзный актёр | эмоциональная закрытость | потеря роли / самоуважения | serialized | character-led |
| Kate: голос | Kate | вернуть уверенность через пение | страх/паника | останется в тени | serialized | character-led |
| Randall: отец | Randall | построить отношения с биологическим отцом | болезнь отца, сопротивление Бет | потеря шанса узнать отца | serialized | character-led |
| Flashback: Jack+дети | Jack | быть хорошим отцом всем троим | разные потребности детей | ревность между детьми | episodic (в рамках эпизода) | character-led |

**Что НЕ линия:**
- «Бет против» — не отдельная линия Бет, а obstacle в линии Рэндалла (пока у Бет нет своей цели)

**Проход 2 — события:**

| event | storyline | function |
|-------|-----------|----------|
| Кевин не может заплакать | Kevin: актёр | setup |
| Режиссёр грозит заменой | Kevin: актёр | escalation |
| Кейт записывается на курсы | Kate: голос | setup |
| Кейт паникует | Kate: голос | escalation |
| Рэндалл узнаёт о болезни отца | Randall: отец | turning_point |
| Бет против визита | Randall: отец | obstacle/escalation |
| Flashback: Кевин ревнует | Flashback + Kevin: актёр (double bump) | setup (flashback) / background (Kevin) |
| Джек берёт Кевина на стройку | Flashback | resolution |
| «Ты особенный по-своему» | Flashback + Kevin: актёр (double bump) | resolution (flashback) / thematic echo (Kevin) |

**Тематическая связь:** флэшбек про «ты особенный» рифмуется с линией Кевина-актёра — он не может заплакать потому что всю жизнь закрывался. Тема эпизода: уязвимость как сила.
