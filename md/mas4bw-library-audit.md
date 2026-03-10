# Технический аудит mas4bw: выделение ядра в библиотеку

## Текущая архитектура

mas4bw — монолитное приложение с четырьмя слоями:

1. **Скрипты обработки** (`main.py`, `main_ru.py`, `main_synopsis.py`) — точки входа
2. **Ядро экстракции** — LangGraph стейт-машина из 9 шагов, ~8-9 вызовов LLM на эпизод
3. **Хранение** — SQLite (SQLModel) + ChromaDB (векторный поиск)
4. **API + фронтенд** — FastAPI + React дашборд

## Ядро экстракции: 9 шагов графа

1. `initialize_state` — читает тексты серий с диска
2. `identify_present_season_arcs_batch` — **запрос в БД** за известными арками + LLM
3. `extract_anthology_arcs_strict` — LLM: антологические линии
4. `extract_soap_and_genre_arcs` — LLM: отношения + жанровые линии
5. `optimize_arcs_with_season_context` — LLM: оптимизация в контексте сезона
6. `deduplicate_arcs` — LLM: дедупликация
7. `enhance_arcs_batch` — LLM: обогащение персонажами
8. `verify_arcs_batch` — LLM: верификация прогрессий и персонажей
9. `final_verify_arcs` — LLM: финальная проверка

Вход: тексты серий + список персонажей + ранее найденные арки
Выход: `List[IntermediateNarrativeArc]` — структурированные сюжетные линии

## Связанность с другими слоями

| Слой | Связанность | Комментарий |
|---|---|---|
| БД (SQLite) | **Высокая** | Шаг 2 графа лезет в БД за предыдущими арками — главный блокер |
| Файловая система | Средняя | 4 файла читаются в `initialize_state`, 1 пишется на выходе |
| Конфигурация | Средняя | `os.getenv()` разбросан по коду, нет центрального конфига |
| API (FastAPI) | **Ноль** | Полностью независимы |
| Фронтенд (React) | **Ноль** | Полностью независимы |

## Что нужно для чистого `extract_arcs()`

### 1. Убрать запрос в БД из графа (~30 строк)
Шаг 2 (`identify_present_season_arcs_batch`) открывает сессию SQLite.
Решение: принимать `known_arcs: list[dict]` как параметр. Пустой список при первом запуске.

### 2. Заменить файловый I/O на передачу в память
`initialize_state` читает 4 файла. Вместо `file_paths` → аргументы `episode_plot: str`, `season_plot: str` и т.д.
Механическая работа.

### 3. Объединить EN и RU дубликаты
Два графа — полная копипаста (~600 строк каждый), отличаются только промптами.
Решение: один граф + `language` параметр + селектор промптов.

### 4. Убрать запись файла на выходе (2 строки)
Возвращать список вместо записи в файл.

## Целевой интерфейс

```python
from mas4bw import extract_arcs

arcs = extract_arcs(
    episodes=["текст серии 1", "текст серии 2", ...],
    language="ru",
    genre="drama",
    known_arcs=[],  # пусто при первом запуске
    llm_provider="anthropic",  # или "openai"
)

for arc in arcs:
    print(arc.title)        # "Мередит и Дерек"
    print(arc.type)          # "soap"
    print(arc.characters)    # ["Мередит", "Дерек"]
    print(arc.episodes)      # [1, 3, 5, 7, 8]
```

## Зависимости пакета

**Обязательные:** langgraph, langchain-core, langchain-openai/langchain-anthropic, pydantic
**Опциональные (предобработка):** spacy, natasha (русский NLP)

## Оценка сроков

| Объём | Срок |
|---|---|
| Чистый `extract_arcs()` — ядро без файлов и БД | 2–4 дня |
| + NLP предобработка (spaCy, Natasha) | +1–2 недели |
| + тесты, документация, публикация на PyPI | 3–4 недели всего |

## Ключевые файлы

- `src/langgraph_narrative_arcs_extraction/narrative_arc_graph_optimized.py` — EN граф
- `src/langgraph_narrative_arcs_extraction/ru_narrative_arc_graph_optimized.py` — RU граф
- `src/narrative_storage_management/prompts.py` — все промпты
- `main_synopsis.py` — уже упрощённый пайплайн, ближе всего к целевому интерфейсу

## Вывод

Реалистично. `main_synopsis.py` — уже 70% нужного интерфейса. Главная работа — вынести БД из графа и объединить языковые дубликаты. Прагматичный путь: начать с версии без предобработки (пользователь подаёт чистые синопсисы), NLP-пайплайн добавить позже как опцию.
