from transformers import pipeline

class AIHelper:
    def __init__(self):
        # Используем маленькую модель для быстрых ответов
        self.generator = pipeline('text-generation', 
                                model='sberbank-ai/mGPT-small-ru',
                                max_length=100)

    async def get_response(self, question: str) -> str:
        try:
            # Добавляем контекст о строительных материалах
            prompt = f"Вопрос о строительных материалах: {question}\nОтвет:"
            response = self.generator(prompt, max_length=150, num_return_sequences=1)
            return response[0]['generated_text'].split("Ответ:")[1].strip()
        except Exception as e:
            return "Извините, я сейчас не могу ответить на этот вопрос. Попробуйте переформулировать."
