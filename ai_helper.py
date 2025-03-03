from deeperseek import DeepSeek

# Авторизация через session token
SESSION_TOKEN = "7kmDEdkwc5Ifko5s+oiWL7Ak/gtnxyO5n00jPruvGVI00vSGq0dMXjqkwfHtETiA"

class AIHelper:
    def __init__(self):
        self.client = DeepSeek(token=SESSION_TOKEN, headless=True)

    async def ask(self, question):
        await self.client.initialize()  # Обязательная инициализация
        response = await self.client.send_message(
            question,
            slow_mode=True,
            deepthink=False,
            search=False,
            slow_mode_delay=0.25
        )
        return response.text  # Возвращает текст ответа

    async def reset_chat(self):
        await self.client.reset_chat()  # Очистка чата

ai_helper = AIHelper()