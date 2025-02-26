import os
import aiohttp
import json
from typing import Optional, Dict

class AIHelper:
    def __init__(self):
        self.api_token = os.getenv("HUGGINGFACE_API_KEY")
        self.api_url = "https://api-inference.huggingface.co/models/sberbank-ai/rugpt3small_based_on_gpt2"
        self.headers = {"Authorization": f"Bearer {self.api_token}"}
        # Улучшенный контекст с информацией о строительных материалах
        self.context = """
        Я - эксперт по строительным материалам с обширными знаниями о:
        - Напольных покрытиях (ламинат, паркет)
        - Стеновых материалах (краска, обои)
        - Плитке (керамическая плитка, керамогранит)

        Я помогаю выбрать оптимальные материалы для ремонта и строительства,
        учитывая соотношение цена/качество, долговечность и особенности применения.

        Вопрос: {question}

        Развернутый ответ эксперта:
        """

    async def get_response(self, question: str) -> str:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.api_url,
                    headers=self.headers,
                    json={
                        "inputs": self.context.format(question=question),
                        "parameters": {
                            "max_length": 300,  # Увеличили длину для более подробных ответов
                            "temperature": 0.7,
                            "num_return_sequences": 1,
                            "top_p": 0.9,  # Добавили top_p для лучшего качества ответов
                            "stop": ["\n\n", "Вопрос:", "Question:"]
                        }
                    }
                ) as response:
                    if response.status != 200:
                        return "Извините, произошла ошибка при обработке вашего вопроса. Пожалуйста, попробуйте позже."

                    result = await response.json()
                    if isinstance(result, list) and len(result) > 0:
                        generated_text = result[0].get('generated_text', '')
                        # Улучшенная обработка ответа
                        answer_parts = generated_text.split('Развернутый ответ эксперта:')
                        if len(answer_parts) > 1:
                            return answer_parts[1].strip()
                        return generated_text.strip()

                    return "Извините, не удалось сгенерировать ответ. Попробуйте переформулировать вопрос."

        except Exception as e:
            print(f"Error in get_response: {e}")
            return "Извините, произошла ошибка. Пожалуйста, попробуйте позже."