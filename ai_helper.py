import os
import logging
import asyncio
from DeeperSeek import DeepSeek

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AIHelper:
    def __init__(self):
        self.api = DeepSeek(
            email="none",
            password="none",
            token="7kmDEdkwc5Ifko5s+oiWL7Ak/gtnxyO5n00jPruvGVI00vSGq0dMXjqkwfHtETiA",
            chat_id="none",  # Optional, can be None
            chrome_args=[],
            verbose=False,
            headless=True,
            attempt_cf_bypass=True
        )

    async def initialize_api(self):
        await self.api.initialize()

    async def get_response(self, question: str) -> str:
        try:
            logger.info(f"Отправка запроса к DeeperSeek API. Вопрос: {question}")
            response = await self.api.ask_question(question)
            logger.info(f"Получен ответ от DeeperSeek API: {response}")
            return response
        except Exception as e:
            logger.error(f"Ошибка в get_response: {str(e)}", exc_info=True)
            return "Произошла ошибка при обработке запроса. Пожалуйста, попробуйте позже."

# Пример использования
async def main():
    ai_helper = AIHelper()
    await ai_helper.initialize_api()
    response = await ai_helper.get_response("Какой ламинат лучше выбрать для кухни?")
    print(response)

if __name__ == "__main__":
    asyncio.run(main())