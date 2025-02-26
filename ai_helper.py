import os
import aiohttp
import json
import logging
from typing import Optional, Dict

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AIHelper:
    def __init__(self):
        self.api_token = os.getenv("HUGGINGFACE_API_KEY")
        if not self.api_token:
            logger.error("HUGGINGFACE_API_KEY не найден в переменных окружения!")
        # Используем модель deepseek-coder
        self.api_url = "https://api-inference.huggingface.co/models/deepseek-ai/deepseek-coder-7b-instruct"
        self.headers = {"Authorization": f"Bearer {self.api_token}"}
        # Расширенный контекст для строительной тематики
        self.context = """
        Инструкция: Ты - эксперт по строительным материалам с глубокими знаниями в области:
        1. Напольных покрытий:
           - Ламинат (классы прочности, типы замков)
           - Паркет (массив, инженерная доска)
           - Плитка (керамогранит, керамическая)
        2. Стеновых материалов:
           - Краски (водоэмульсионные, акриловые, силиконовые)
           - Обои (виниловые, флизелиновые, стеклообои)
           - Декоративная штукатурка
        3. Технических характеристик:
           - Износостойкость
           - Влагостойкость
           - Экологичность

        Отвечай подробно, но по делу, давай практические рекомендации.

        Вопрос: {question}

        Ответ эксперта:"""

    async def get_response(self, question: str) -> str:
        try:
            logger.info(f"Отправка запроса к API. Вопрос: {question}")

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.api_url,
                    headers=self.headers,
                    json={
                        "inputs": self.context.format(question=question),
                        "parameters": {
                            "max_length": 300,  # Уменьшили для более быстрых ответов
                            "temperature": 0.7,  # Баланс между креативностью и точностью
                            "top_p": 0.9,
                            "num_return_sequences": 1,
                            "do_sample": True,
                            "repetition_penalty": 1.2,  # Добавили штраф за повторения
                            "stop": ["\n\nВопрос:", "\n\nИнструкция:"]
                        }
                    }
                ) as response:
                    if response.status != 200:
                        error_info = await response.text()
                        logger.error(f"Ошибка API: {error_info}")
                        if "Model not found" in error_info or "does not exist" in error_info:
                            return "Извините, выбранная модель AI недоступна. Пожалуйста, попробуйте позже или обратитесь к администратору."
                        return "Извините, сервис временно недоступен. Пожалуйста, попробуйте позже."

                    result = await response.json()
                    logger.info(f"Получен ответ от API: {result}")

                    if isinstance(result, list) and len(result) > 0:
                        generated_text = result[0].get('generated_text', '')
                        logger.info(f"Сгенерированный текст: {generated_text}")

                        # Извлекаем ответ после маркера
                        answer_parts = generated_text.split('Ответ эксперта:')
                        if len(answer_parts) > 1:
                            answer = answer_parts[1].strip()
                            # Очищаем от лишних переносов строк и форматируем
                            answer = ' '.join(answer.split())
                            logger.info(f"Обработанный ответ: {answer[:100]}...")
                            return answer[:1000]  # Ограничиваем длину ответа

                        logger.warning("Не удалось найти маркер 'Ответ эксперта' в ответе")
                        return generated_text.strip()[:1000]

                    logger.warning("Неожиданный формат ответа от API")
                    return "Извините, не удалось сгенерировать ответ. Попробуйте задать вопрос иначе."

        except Exception as e:
            logger.error(f"Ошибка в get_response: {str(e)}", exc_info=True)
            return "Произошла ошибка при обработке запроса. Пожалуйста, попробуйте позже."