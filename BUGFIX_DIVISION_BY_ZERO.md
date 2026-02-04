# Исправление: ZeroDivisionError при экспорте результатов

## Проблема

При экспорте результатов анализа в Excel возникала ошибка:
```python
ZeroDivisionError: division by zero
File "D:\Ermolino\Stock_Quotes\src\excel_exporter.py", line 233, in _create_quality_sheet
    'Разных мнений': f"{sum(d['Разных мнений'] for d in quality_data) / len(quality_data):.1f}",
```

**Причина:** Когда список `quality_data` пустой (нет результатов анализа), происходило деление на `len(quality_data)`, что равно 0.

## Решение ✅

### Исправленные файлы

#### 1. `src/excel_exporter.py` (2 исправления)

**Проблема 1:** Деление на `len(quality_data)` при создании итоговой статистики
```python
# БЫЛО (строка 233):
'Разных мнений': f"{sum(d['Разных мнений'] for d in quality_data) / len(quality_data):.1f}",

# СТАЛО:
if not quality_data:
    # Создаем пустой лист с сообщением
    df = pd.DataFrame([{'Тикер': 'Нет данных', ...}])
    df.to_excel(writer, sheet_name='Анализ качества', index=False)
    logger.warning("Нет данных для анализа качества")
    return

# Далее вычисления с проверкой
total_count = len(quality_data)
avg_opinions = sum(d['Разных мнений'] for d in quality_data) / total_count
```

**Проблема 2:** Деление на `len(confidences)` при расчете средней уверенности
```python
# БЫЛО (строка 212):
avg_conf = sum(conf_map.get(c, 1) for c in confidences) / len(confidences)

# СТАЛО:
if confidences:
    avg_conf = sum(conf_map.get(c, 1) for c in confidences) / len(confidences)
    avg_conf_text = 'ВЫСОКАЯ' if avg_conf >= 2.5 else (
        'СРЕДНЯЯ' if avg_conf >= 1.5 else 'НИЗКАЯ'
    )
else:
    avg_conf_text = 'Н/Д'
```

#### 2. `src/data_loader.py`

**Проблема:** Деление на `len(stocks)` при расчете статистики
```python
# БЫЛО (строки 223-224):
'avg_price': sum(s['price'] for s in stocks) / len(stocks),
'avg_change': sum(s['change'] for s in stocks) / len(stocks),

# СТАЛО:
total = len(stocks)
'avg_price': sum(s['price'] for s in stocks) / total if total > 0 else 0,
'avg_change': sum(s['change'] for s in stocks) / total if total > 0 else 0,
```

#### 3. `src/dashboards/overview.py` (4 исправления)

**Проблема 1:** Деление на `len(predictions)` при расчете консенсуса
```python
# БЫЛО (строка 101):
data['agreement'] = predictions.count(most_common) / len(predictions) * 100

# СТАЛО:
if predictions:
    most_common = max(set(predictions), key=predictions.count)
    data['consensus'] = most_common
    data['agreement'] = predictions.count(most_common) / len(predictions) * 100
else:
    data['consensus'] = 'Н/Д'
    data['agreement'] = 0
```

**Проблема 2-3:** Деление на `len(stocks_data)` при отображении метрик
```python
# БЫЛО (строки 120, 128, 132):
delta=f"{growing/len(stocks_data)*100:.0f}%"
delta=f"-{falling/len(stocks_data)*100:.0f}%"
avg_agreement = sum(s['agreement'] for s in stocks_data.values()) / len(stocks_data)

# СТАЛО:
total_stocks = len(stocks_data)
delta=f"{growing/total_stocks*100:.0f}%" if total_stocks > 0 else "0%"
delta=f"-{falling/total_stocks*100:.0f}%" if total_stocks > 0 else "0%"
avg_agreement = sum(s['agreement'] for s in stocks_data.values()) / total_stocks if total_stocks > 0 else 0
```

**Проблема 4:** Деление на `len(stocks_data)` при расчете статистики
```python
# БЫЛО (строки 180, 184-185):
st.markdown(f"**Моделей:** {len(results) // len(stocks_data)}")
avg_price = sum(s['price'] for s in stocks_data.values()) / len(stocks_data)
avg_change = sum(s['change'] for s in stocks_data.values()) / len(stocks_data)

# СТАЛО:
total_stocks = len(stocks_data)
models_count = len(results) // total_stocks if total_stocks > 0 else 0
st.markdown(f"**Моделей:** {models_count}")
avg_price = sum(s['price'] for s in stocks_data.values()) / total_stocks if total_stocks > 0 else 0
avg_change = sum(s['change'] for s in stocks_data.values()) / total_stocks if total_stocks > 0 else 0
```

## Итого

### Исправлено файлов: 3
- `src/excel_exporter.py` - 2 проблемы
- `src/data_loader.py` - 1 проблема
- `src/dashboards/overview.py` - 4 проблемы

### Всего исправлений: 7

## Паттерн защиты

Во всех случаях применён единый паттерн защиты от деления на ноль:

```python
# Вариант 1: Проверка перед делением
if len(data) > 0:
    result = sum(data) / len(data)
else:
    result = default_value

# Вариант 2: Тернарный оператор
total = len(data)
result = sum(data) / total if total > 0 else default_value

# Вариант 3: Ранний возврат
if not data:
    return empty_result
# ... продолжить вычисления
```

## Тестирование

После исправлений приложение корректно обрабатывает следующие сценарии:

1. ✅ Экспорт пустых результатов (создаётся лист с сообщением "Нет данных")
2. ✅ Отображение метрик без данных (показывает 0 или "Н/Д")
3. ✅ Расчет статистики для пустых списков (возвращает 0)
4. ✅ Консенсус прогнозов без предсказаний (показывает "Н/Д")

## Дополнительные проверки

Файлы, которые уже были защищены от деления на ноль:

- ✅ `src/analyzer.py:325` - есть проверка `if stocks_data else 0`
- ✅ `src/llm_manager.py:367` - есть проверка `if confidences else 1`

## Рекомендации

Для предотвращения подобных ошибок в будущем:

1. **Всегда проверяйте длину** перед делением на неё
2. **Используйте защитные значения** (default values) для пустых коллекций
3. **Добавляйте логирование** для граничных случаев
4. **Пишите тесты** для пустых входных данных

---

**Дата исправления:** 2026-02-04  
**Затронуто файлов:** 3  
**Всего исправлений:** 7  
**Статус:** ✅ Исправлено и протестировано
