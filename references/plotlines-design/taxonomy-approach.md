# Подход: нормализация тегов через масштаб

## Проблема

После извлечения цитат из нескольких книг получается ~500 topics, где одно и то же называется по-разному (Nash: "franchise types", Douglas: "episodic forms"). Фильтровать и группировать невозможно.

## Решение: двухуровневая таксономия

Каждой цитате присваиваем два поля:

**`level`** — масштаб, к которому относится цитата:
- `serial` — сериал целиком (франшиза, story engine, мир, тон)
- `season` — сезонная арка, сериализация, A/B/C линии, тема
- `episode` — структура эпизода (акты, beat sheet, teaser, пилот)
- `scene` — сцена, dramatic beat, диалог, подтекст
- `character` — арки персонажей, антагонист, эмпатия, ансамбль
- `docs` — документация (pitch, bible, proposal, spec script)
- `industry` — writers room, development cycle, карьера

**`tag`** — конкретная сущность внутри уровня:
`beat-sheet`, `act-structure`, `cold-open`, `story-engine`, `pitch-oral`, `writers-room` и т.д.

## Почему масштаб в основе

- **Объективный критерий** — цитата про сцену или про сезон определяется однозначно, не зависит от мнения
- **Иерархия даёт навигацию** — пользователь идёт сверху вниз: сериал → сезон → эпизод → сцена
- **Совместимо с wizard** — шаги от общего к частному
- **Новые книги ложатся без переделки** — добавляешь tags внутри существующих levels

## Дерево тем (построено из 7 оглавлений)

### Источники

| # | Книга | Автор |
|---|-------|-------|
| 1 | Save the Cat! Writes for TV | Nash |
| 2 | Writing the TV Drama Series | Douglas |
| 3 | The TV Showrunner's Roadmap | Landau |
| 4 | Series Bible guide | Pena & Ziza |
| 5 | Inside the Room | Venis (ed.) |
| 6 | Showrunners | Bennett |
| 7 | Non-User-Friendly Guide | Sears |

### Структура

```
СЕРИАЛ (целое)
├── franchise type / story engine          Nash 1-2, Landau 4, Douglas Ch1
├── world building / setting               Landau 3
├── tone / genre / format                  Nash 4, Bennett Ch4, Landau 10,13
│
├── СЕЗОН
│   ├── season arc / long narrative        Nash 6, Douglas Ch1-2
│   ├── serialized vs procedural           Bennett Ch2, Douglas Ch1
│   ├── A/B/C storylines                   Nash 3, Douglas Ch3
│   ├── theme                              Landau 11
│   ├── cliffhangers                       Landau 12
│   │
│   ├── ЭПИЗОД
│   │   ├── act structure (4/5/6 acts)     Douglas Ch3, Bennett Ch2
│   │   ├── beat sheet                     Nash 5,10,11
│   │   ├── teaser / cold open             Douglas Ch3, Nash Cold Open
│   │   ├── pilot (особый эпизод)          Nash7-9, Douglas Ch4, Venis 3, Bennett Ch2
│   │   │
│   │   ├── СЦЕНА
│   │   │   ├── dramatic beat              Douglas Ch3
│   │   │   ├── scene construction         Douglas Ch3-4
│   │   │   └── dialogue / subtext         Landau 8
│   │   │
│   │   └── SCRIPT
│   │       ├── outline / board            Nash 12-13, Douglas Ch4
│   │       ├── script format              Douglas Ch4, Venis 1-2
│   │       └── drafts / polish            Douglas Ch4, Venis 4
│   │
│   └── ПЕРСОНАЖ
│       ├── character arc (series vs film) Douglas Ch1, Landau 5
│       ├── antagonist                     Landau 9
│       ├── empathy / rooting interest     Landau 5, Douglas Ch4
│       └── ensemble / family dynamics     Landau 6, Nash 2
│
├── ДОКУМЕНТАЦИЯ
│   ├── pitch (устный)                     Nash 14, Landau 14, Pena&Ziza
│   ├── proposal / one-sheet               Pena&Ziza
│   ├── series bible                       Pena&Ziza, Douglas Ch2
│   └── spec script                        Venis 1-2, Sears
│
└── ИНДУСТРИЯ
    ├── writers room / staff               Douglas Ch5, Bennett Ch2,5
    ├── development cycle                  Douglas Ch2, Bennett Ch2
    ├── breaking in                        Douglas Ch6, Sears, Venis 9
    └── showrunning                        Bennett Ch1,5, Sears
```

## Как применять

1. Построить дерево из оглавлений всех книг (что мы сделали)
2. Вывести ~30-50 нормализованных tags
3. Прогнать все цитаты через классификацию: каждая получает `level` + `tag`
4. Viewer группирует по level, фильтрует по tag
5. Когда все книги прочитаны — каждый tag становится концепцией на Pass 2

## Что это даёт

- Вместо 400 кнопок-тем → 7 уровней × 5-8 тегов = управляемая навигация
- Цитаты из разных книг по одной теме собираются вместе автоматически
- Таксономия растёт из самих книг (bottom-up), но организована по объективному принципу (масштаб)
