import os
import aiohttp
import json
import logging
import asyncio
from typing import Optional, Dict

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AIHelper:
    def __init__(self):
        self.api_token = os.getenv("HUGGINGFACE_API_KEY")
        if not self.api_token:
            logger.error("HUGGINGFACE_API_KEY не найден в переменных окружения!")

        # Основная и резервная модели
        self.models = [
            "mistralai/Mistral-7B-Instruct-v0.3",
            "mistralai/Mixtral-8x7B-Instruct-v0.1"
        ]
        self.current_model_index = 0
        self.headers = {"Authorization": f"Bearer {self.api_token}"}

        # Параметры для повторных попыток
        self.max_retries = 3
        self.base_delay = 2  # начальная задержка в секундах

        # Контекст для модели
        self.context = """<s>[INST] Ты - эксперт по стройматериалам. Отвечай кратко и по делу, в 2-3 предложения. Фокусируйся на главном:
- для напольных покрытий: класс прочности, влагостойкость, применение
- для стеновых материалов: тип, особенности нанесения, долговечность
- для технических характеристик: ключевые параметры и рекомендации

Вопрос: {question} [/INST]

Ответ:</s>"""

    async def make_request(self, question: str, retry_count: int = 0) -> Dict:
        model = self.models[self.current_model_index]
        api_url = f"https://api-inference.huggingface.co/models/{model}"

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    api_url,
                    headers=self.headers,
                    json={
                        "inputs": self.context.format(question=question),
                        "parameters": {
                            "max_new_tokens": 200,  # Уменьшили для более кратких ответов
                            "temperature": 0.5,  # Снизили для более конкретных ответов
                            "top_p": 0.85,
                            "num_return_sequences": 1,
                            "do_sample": True,
                            "repetition_penalty": 1.2,  # Увеличили штраф за повторения
                            "return_full_text": False
                        }
                    }
                ) as response:
                    if response.status == 200:
                        return await response.json()

                    error_info = await response.text()
                    logger.error(f"Ошибка API (модель: {model}, попытка {retry_count + 1}): {error_info}")

                    if "overloaded" in error_info.lower():
                        # Пробуем другую модель, если текущая перегружена
                        if self.current_model_index < len(self.models) - 1:
                            logger.info(f"Переключаемся на следующую модель: {self.models[self.current_model_index + 1]}")
                            self.current_model_index += 1
                            return await self.make_request(question, retry_count)

                        # Если все модели перепробовали, используем повторные попытки
                        if retry_count < self.max_retries:
                            delay = self.base_delay * (2 ** retry_count)
                            logger.info(f"Все модели перегружены. Повторная попытка через {delay} секунд...")
                            await asyncio.sleep(delay)
                            self.current_model_index = 0  # Сбрасываем на первую модель
                            return await self.make_request(question, retry_count + 1)
                        return {"error": "overloaded"}

                    return {"error": error_info}
        except Exception as e:
            logger.error(f"Ошибка запроса (попытка {retry_count + 1}): {str(e)}", exc_info=True)
            return {"error": str(e)}

    async def get_response(self, question: str) -> str:
        try:
            logger.info(f"Отправка запроса к API. Вопрос: {question}")

            result = await self.make_request(question)

            if "error" in result:
                if result["error"] == "overloaded":
                    return ("Извините, все доступные модели сейчас перегружены. Я попытался несколько раз получить ответ, "
                           "но пока не получается. Пожалуйста, подождите немного и попробуйте снова.")
                return f"Извините, произошла ошибка при обработке запроса. Пожалуйста, попробуйте позже."

            logger.info(f"Получен ответ от API: {result}")

            if isinstance(result, list) and len(result) > 0:
                generated_text = result[0].get('generated_text', '')
                logger.info(f"Сгенерированный текст: {generated_text}")

                # Очищаем текст от специальных токенов и форматируем
                answer = generated_text.replace('</s>', '').strip()
                answer = ' '.join(answer.split())
                logger.info(f"Обработанный ответ: {answer[:100]}...")
                return answer[:1000]  # Ограничиваем длину ответа

            logger.warning("Неожиданный формат ответа от API")
            return "Извините, не удалось сгенерировать ответ. Попробуйте задать вопрос иначе."

        except Exception as e:
            logger.error(f"Ошибка в get_response: {str(e)}", exc_info=True)
            return "Произошла ошибка при обработке запроса. Пожалуйста, попробуйте позже."