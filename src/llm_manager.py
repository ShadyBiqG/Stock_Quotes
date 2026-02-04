"""
Менеджер для работы с OpenRouter API
Поддержка множественных LLM моделей с защитой от галлюцинаций
"""

import logging
from typing import Dict, List, Optional
from datetime import datetime
import re
import asyncio
import aiohttp
from openai import OpenAI

logger = logging.getLogger(__name__)


class OpenRouterClient:
    """Клиент для работы с OpenRouter API"""
    
    # Подозрительные паттерны для детектирования галлюцинаций
    SUSPICIOUS_KEYWORDS = [
        'новость', 'объявил', 'сообщил', 'согласно источникам',
        'CEO', 'отчет показал', 'аналитики говорят', 'эксперты считают',
        'было объявлено', 'компания планирует', 'инсайдеры утверждают'
    ]
    
    def __init__(self, api_key: str, base_url: str = "https://openrouter.ai/api/v1"):
        """
        Инициализация клиента
        
        Args:
            api_key: OpenRouter API ключ
            base_url: Базовый URL API
        """
        if not api_key or api_key == "your-openrouter-api-key-here":
            raise ValueError(
                "OpenRouter API ключ не настроен! "
                "Укажите его в config.yaml или переменной окружения OPENROUTER_API_KEY"
            )
        
        self.client = OpenAI(
            api_key=api_key,
            base_url=base_url
        )
        self.base_url = base_url
        self.api_key = api_key
        
        logger.info("OpenRouter клиент инициализирован")
    
    def analyze(self, 
                model_id: str,
                model_name: str,
                system_prompt: str,
                user_prompt: str,
                temperature: float = 0.3,
                max_tokens: int = 1000) -> Dict:
        """
        Запрос к одной модели
        
        Args:
            model_id: ID модели в OpenRouter
            model_name: Название модели
            system_prompt: Системный промпт
            user_prompt: Промпт пользователя
            temperature: Температура (креативность)
            max_tokens: Максимум токенов
            
        Returns:
            Словарь с результатом анализа
        """
        logger.info(f"Запрос к модели: {model_name}")
        
        try:
            response = self.client.chat.completions.create(
                model=model_id,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=temperature,
                max_tokens=max_tokens
            )
            
            raw_response = response.choices[0].message.content
            tokens_used = response.usage.total_tokens if response.usage else 0
            finish_reason = response.choices[0].finish_reason
            
            logger.info(f"Получен ответ от {model_name} ({tokens_used} токенов, finish_reason: {finish_reason})")
            
            # Проверка на обрезанный ответ
            if finish_reason == 'length':
                logger.warning(
                    f"⚠️ Ответ от {model_name} был обрезан из-за лимита токенов! "
                    f"Рекомендуется увеличить max_tokens (текущий: {max_tokens})"
                )
            
            # Парсинг ответа
            parsed = self._parse_response(raw_response)
            
            # Валидация на галлюцинации
            validation = self._validate_response(raw_response, parsed)
            
            # Добавляем информацию об обрезке в валидацию
            if finish_reason == 'length':
                validation['truncated'] = True
                validation['trust_level'] = 'LOW'
                logger.warning(f"Снижение доверия для {model_name} из-за обрезки ответа")
            
            result = {
                'model_name': model_name,
                'model_id': model_id,
                'prediction': parsed.get('prediction', 'НЕИЗВЕСТНО'),
                'analysis_text': parsed.get('analysis_text', ''),
                'key_factors': parsed.get('key_factors', []),
                'reasons': parsed.get('reasons', []),  # Для обратной совместимости
                'confidence': parsed.get('confidence', 'НИЗКАЯ'),
                'raw_response': raw_response,
                'validation_flags': validation,
                'timestamp': datetime.now().isoformat(),
                'tokens_used': tokens_used,
                'success': True
            }
            
            return result
            
        except Exception as e:
            logger.error(f"Ошибка запроса к {model_name}: {e}")
            return {
                'model_name': model_name,
                'model_id': model_id,
                'prediction': 'ОШИБКА',
                'reasons': [f"Ошибка запроса: {str(e)}"],
                'confidence': 'НИЗКАЯ',
                'raw_response': '',
                'validation_flags': {'error': True},
                'timestamp': datetime.now().isoformat(),
                'tokens_used': 0,
                'success': False,
                'error': str(e)
            }
    
    async def analyze_async(self,
                           model_id: str,
                           model_name: str,
                           system_prompt: str,
                           user_prompt: str,
                           temperature: float = 0.3,
                           max_tokens: int = 1000) -> Dict:
        """
        Асинхронный запрос к модели
        
        Args:
            См. analyze()
            
        Returns:
            Словарь с результатом
        """
        # Используем синхронный клиент в executor для асинхронности
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            self.analyze,
            model_id, model_name, system_prompt, user_prompt, temperature, max_tokens
        )
    
    async def analyze_all_async(self,
                               models: List[Dict],
                               system_prompt: str,
                               user_prompt: str) -> List[Dict]:
        """
        Параллельный запрос ко всем моделям
        
        Args:
            models: Список конфигураций моделей
            system_prompt: Системный промпт
            user_prompt: Промпт пользователя
            
        Returns:
            Список результатов от всех моделей
        """
        tasks = []
        
        for i, model in enumerate(models):
            # Небольшая задержка между запусками для снижения rate limiting
            if i > 0:
                await asyncio.sleep(0.5)  # 500ms между запусками моделей
            
            task = self.analyze_async(
                model_id=model['id'],
                model_name=model['name'],
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=model.get('temperature', 0.3),
                max_tokens=model.get('max_tokens', 2000)  # Увеличенное значение по умолчанию
            )
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Обработка исключений
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Ошибка в модели {models[i]['name']}: {result}")
                processed_results.append({
                    'model_name': models[i]['name'],
                    'model_id': models[i]['id'],
                    'prediction': 'ОШИБКА',
                    'reasons': [str(result)],
                    'confidence': 'НИЗКАЯ',
                    'success': False,
                    'error': str(result)
                })
            else:
                processed_results.append(result)
        
        return processed_results
    
    def _parse_response(self, response: str) -> Dict:
        """
        Парсинг структурированного ответа модели
        
        Args:
            response: Сырой текст ответа
            
        Returns:
            Словарь с распарсенными полями
        """
        parsed = {
            'prediction': 'НЕИЗВЕСТНО',
            'analysis_text': '',
            'key_factors': [],
            'reasons': [],  # Для обратной совместимости
            'confidence': 'НИЗКАЯ'
        }
        
        # Проверка длины ответа
        if len(response) < 100:
            logger.warning(
                f"⚠️ Очень короткий ответ ({len(response)} символов): {response[:50]}..."
            )
        
        # Парсинг прогноза
        prediction_match = re.search(
            r'ПРОГНОЗ:\s*(РАСТЕТ|ПАДАЕТ|СТАБИЛЬНА)',
            response,
            re.IGNORECASE
        )
        if prediction_match:
            parsed['prediction'] = prediction_match.group(1).upper()
        
        # Парсинг секции АНАЛИЗ
        analysis_section = re.search(
            r'АНАЛИЗ:\s*(.*?)(?=КЛЮЧЕВЫЕ ФАКТОРЫ:|УВЕРЕННОСТЬ:|$)',
            response,
            re.DOTALL | re.IGNORECASE
        )
        if analysis_section:
            analysis_text = analysis_section.group(1).strip()
            # Очистка от лишних символов
            analysis_text = re.sub(r'\[.*?\]', '', analysis_text)  # Удаляем инструкции в []
            analysis_text = analysis_text.strip()
            if analysis_text:
                parsed['analysis_text'] = analysis_text
        
        # Парсинг КЛЮЧЕВЫХ ФАКТОРОВ
        factors_section = re.search(
            r'КЛЮЧЕВЫЕ ФАКТОРЫ:\s*(.*?)(?=УВЕРЕННОСТЬ:|$)',
            response,
            re.DOTALL | re.IGNORECASE
        )
        if factors_section:
            factors_text = factors_section.group(1)
            # Ищем строки начинающиеся с • или цифры
            factors = re.findall(r'[•\-\*]\s*(.+?)(?=\n[•\-\*]|\n\n|$)', factors_text, re.DOTALL)
            if not factors:
                # Попробуем через нумерованный список
                factors = re.findall(r'\d+\.\s*(.+?)(?=\n\d+\.|\n\n|$)', factors_text, re.DOTALL)
            parsed['key_factors'] = [f.strip() for f in factors if f.strip()]
        
        # Парсинг старого формата ПРИЧИНЫ (для обратной совместимости)
        if not parsed['key_factors']:
            reasons_section = re.search(
                r'ПРИЧИНЫ:(.*?)(?=УВЕРЕННОСТЬ:|$)',
                response,
                re.DOTALL | re.IGNORECASE
            )
            if reasons_section:
                reasons_text = reasons_section.group(1)
                reasons = re.findall(r'\d+\.\s*(.+?)(?=\n\d+\.|\n\n|$)', reasons_text, re.DOTALL)
                parsed['reasons'] = [r.strip() for r in reasons if r.strip()]
                # Копируем в key_factors для единообразия
                parsed['key_factors'] = parsed['reasons']
        
        # Парсинг уверенности
        confidence_match = re.search(
            r'УВЕРЕННОСТЬ:\s*(ВЫСОКАЯ|СРЕДНЯЯ|НИЗКАЯ)',
            response,
            re.IGNORECASE
        )
        if confidence_match:
            parsed['confidence'] = confidence_match.group(1).upper()
        
        return parsed
    
    def _validate_response(self, raw_response: str, parsed: Dict) -> Dict:
        """
        Валидация ответа на галлюцинации и корректность
        
        Args:
            raw_response: Сырой ответ
            parsed: Распарсенный ответ
            
        Returns:
            Словарь с флагами валидации
        """
        flags = {
            'format_valid': True,
            'suspicious_patterns': [],
            'trust_level': 'HIGH'
        }
        
        # Проверка формата
        if parsed['prediction'] == 'НЕИЗВЕСТНО':
            flags['format_valid'] = False
            flags['trust_level'] = 'LOW'
        
        # Проверка наличия анализа или факторов (достаточно одного из них)
        has_analysis = bool(parsed.get('analysis_text', '').strip())
        has_factors = bool(parsed.get('key_factors', []))
        has_reasons = bool(parsed.get('reasons', []))
        
        if not (has_analysis or has_factors or has_reasons):
            flags['format_valid'] = False
            flags['trust_level'] = 'LOW'
        elif has_analysis and (has_factors or has_reasons):
            # Если есть и анализ, и факторы - отлично!
            flags['format_valid'] = True
            flags['trust_level'] = 'HIGH'
        elif has_analysis or (has_factors and len(parsed.get('key_factors', [])) >= 2):
            # Если есть анализ или хотя бы 2 фактора - хорошо
            flags['format_valid'] = True
            if parsed.get('confidence') == 'НИЗКАЯ':
                flags['trust_level'] = 'MEDIUM'
            # Не снижаем trust_level если всё остальное в порядке
        
        # Проверка на подозрительные паттерны
        response_lower = raw_response.lower()
        for keyword in self.SUSPICIOUS_KEYWORDS:
            if keyword.lower() in response_lower:
                flags['suspicious_patterns'].append(keyword)
        
        if flags['suspicious_patterns']:
            flags['trust_level'] = 'MEDIUM' if len(flags['suspicious_patterns']) < 3 else 'LOW'
            logger.warning(
                f"Обнаружены подозрительные паттерны: {', '.join(flags['suspicious_patterns'])}"
            )
        
        # Проверка на слишком общие фразы
        generic_phrases = [
            'рыночные условия', 'общий тренд', 'экономическая ситуация',
            'в целом', 'как правило', 'обычно'
        ]
        
        generic_count = sum(1 for phrase in generic_phrases if phrase in response_lower)
        if generic_count > 2:
            flags['trust_level'] = 'MEDIUM'
            logger.warning("Ответ содержит слишком много общих фраз")
        
        return flags
    
    def query(self, prompt: str, model_id: str, temperature: float = 0.1) -> str:
        """
        Простой запрос к модели (для fallback в company_info)
        
        Args:
            prompt: Промпт
            model_id: ID модели
            temperature: Температура
            
        Returns:
            Текст ответа
        """
        try:
            response = self.client.chat.completions.create(
                model=model_id,
                messages=[{"role": "user", "content": prompt}],
                temperature=temperature,
                max_tokens=500
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            logger.error(f"Ошибка простого запроса: {e}")
            raise
    
    def calculate_consensus(self, results: List[Dict]) -> Dict:
        """
        Вычислить консенсус между моделями
        
        Args:
            results: Результаты от всех моделей
            
        Returns:
            Словарь с консенсусом
        """
        if not results:
            return {
                'agreed_prediction': None,
                'disagreement_count': 0,
                'avg_confidence': 'НИЗКАЯ'
            }
        
        # Подсчет прогнозов
        predictions = [r['prediction'] for r in results if r.get('success', False)]
        
        if not predictions:
            return {
                'agreed_prediction': None,
                'disagreement_count': len(results),
                'avg_confidence': 'НИЗКАЯ'
            }
        
        # Наиболее частый прогноз
        prediction_counts = {}
        for pred in predictions:
            prediction_counts[pred] = prediction_counts.get(pred, 0) + 1
        
        most_common = max(prediction_counts.items(), key=lambda x: x[1])
        agreed_prediction = most_common[0] if most_common[1] > 1 else None
        
        disagreement_count = len(predictions) - most_common[1]
        
        # Средняя уверенность
        confidence_map = {'ВЫСОКАЯ': 3, 'СРЕДНЯЯ': 2, 'НИЗКАЯ': 1}
        confidences = [
            confidence_map.get(r['confidence'], 1)
            for r in results if r.get('success', False)
        ]
        
        avg_conf_num = sum(confidences) / len(confidences) if confidences else 1
        
        if avg_conf_num >= 2.5:
            avg_confidence = 'ВЫСОКАЯ'
        elif avg_conf_num >= 1.5:
            avg_confidence = 'СРЕДНЯЯ'
        else:
            avg_confidence = 'НИЗКАЯ'
        
        return {
            'agreed_prediction': agreed_prediction,
            'disagreement_count': disagreement_count,
            'avg_confidence': avg_confidence,
            'all_predictions': predictions
        }


# Пример использования
if __name__ == "__main__":
    import yaml
    logging.basicConfig(level=logging.INFO)
    
    # Загрузка конфигурации
    with open("../config.yaml", 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    
    client = OpenRouterClient(
        api_key=config['openrouter']['api_key']
    )
    
    # Тестовый запрос
    result = client.analyze(
        model_id="openai/gpt-3.5-turbo",
        model_name="GPT-3.5",
        system_prompt=config['system_prompt'],
        user_prompt="Тест"
    )
    
    print(f"Результат: {result['prediction']}")
