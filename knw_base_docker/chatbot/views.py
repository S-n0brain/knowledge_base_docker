import datetime
import json
from typing import List, Literal
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.views.generic import DetailView
from openai import OpenAI
from openai.types.responses.response import Response
from requests import request
from traitlets import Bool
from knowledge_base.settings import API_GPT_KEY
from .forms import ChatForm
from .models import Chat, Message, UserDailyTokens
from knowledge_base_app.models import ArticleChunk
from django.contrib.auth.mixins import LoginRequiredMixin
import tiktoken
from pgvector.django import CosineDistance

class ChatView(LoginRequiredMixin, DetailView):
    BASE_URL_MODAL = "https://api.proxyapi.ru/openai/v1"
    MODEL = "gpt-5-mini" # Модель для генерации ответов
    EMBEDDING_MODEL = "text-embedding-3-small" # Модель для получения эмбеддингов
    K = 3 # Количество наиболее релевантных статей для поиска
    COUNTS_MESSAGE_HISTORY = 15 # Количество сообщений для истории
    DAYS_LIMIT = 90 # Количество дней для удаления старых сообщений
    ENCODING_DEFAULT_NAME = "o200k_base"
    URL_PROXY_API_BALANCE = "https://api.proxyapi.ru/proxyapi/balance"
    TOKENS_PER_DAY = 35000
    MAX_TOKENS_PER_REQUEST = 3000
    template_name = 'chatbot/chat.html'
    form_class = ChatForm
    model = Chat

    def get_context_data(self, **kwargs) -> dict:
        context = super().get_context_data(**kwargs)
        context['form'] = self.form_class()
        context['messages'] = Message.objects.filter(chat=self.get_object()).order_by('created_at').select_related('chat')
        context['balance'] = self.get_balance_proxy_api()
        context['user_tokens_obj'] = UserDailyTokens.objects.get(user=self.request.user)
        return context

    def get_object(self) -> Chat:
        user = self.request.user
        chat, created = Chat.objects.get_or_create(user=user)
        if created:
            # Если чат был создан, добавим в бд информацию о токенах пользователя
            if not UserDailyTokens.objects.filter(user=user).exists():
                UserDailyTokens.objects.create(user=user, tokens_available=self.TOKENS_PER_DAY)
        return chat

    def get(self, request: HttpRequest, *args, **kwargs) -> HttpResponse:
        chat = self.get_object()
        self.delete_old_messages(chat)
        user_tokens_object: UserDailyTokens = UserDailyTokens.objects.get(user=self.request.user)
        self.update_everyday_user_tokens(user_tokens_object)
        return super().get(request, *args, **kwargs)

    @classmethod
    def get_balance_proxy_api(cls):
        # Получаем баланс Proxy_aPI
        try:
            balance = request(method="GET", url=cls.URL_PROXY_API_BALANCE, headers={"Authorization": f"Bearer {API_GPT_KEY}"})
            if balance.status_code == 200:
                return balance.json().get("balance", 0)
            return 0
        except Exception as e:
            print(f'Ошибка получения баланса Proxy API: {e}')
            balance = 0
        return balance

    @classmethod
    def get_client(cls) -> OpenAI:
        return OpenAI(api_key=API_GPT_KEY, base_url=cls.BASE_URL_MODAL)
    
    def post(self, *args, **kwargs) -> JsonResponse:
        data = json.loads(self.request.body)
        chat = self.get_object()
        if data.get("name") == "send_message":
            message = data.get("message", "")
            if message and type(message) is str and self.get_balance_proxy_api() > 0:
                user_tokens, user_tokens_object = self.get_user_tokens()
                message_tokens = self.num_tokens_from_string(message)
                if message_tokens > user_tokens:
                    # Кончились токены
                    return JsonResponse({"no_tokens": True, "user_tokens": user_tokens}, status=429)
                try:
                    client: OpenAI = self.get_client()
                except Exception as e:
                    print(f'Ошибка получения клиента: {e}')
                    return JsonResponse({"error": f"Ошибка получения клиента"}, status=500)
                try:
                    if not data.get("use_rag"):
                        is_rag = False
                        response = self.handle_norrmal_chat(client, chat, message)
                    else:
                        is_rag = True
                        response = self.handle_rag_chat(client, message)
                except Exception as e:
                    print(f'Ошибка получения ответа от модели: {e}')
                    return JsonResponse({"error": f"Ошибка получения ответа от модели"}, status=500)
                self.append_messages_in_bd(chat, message, response, is_rag)
                sum_tokens = response.usage.total_tokens # type: ignore
                # Уменьшаем токены
                user_tokens -= sum_tokens
                if user_tokens_object:
                    user_tokens_object.tokens_available = user_tokens if user_tokens > 0 else 0
                    user_tokens_object.save()
                    self.update_everyday_user_tokens(user_tokens_object)
                return JsonResponse({"reply": response.output_text, "role": "Ассистент",
                                     "model": response.model, "user_tokens": user_tokens, "is_rag": is_rag})
        elif data.get("name") == "clear_chat":
            # Удаляем все сообщения в чате
            Message.objects.filter(chat=chat).delete()
            return JsonResponse({"clear": True})
        return JsonResponse({"error": f"Ошибка сообщения"}, status=400)

    def get_user_tokens(self) -> tuple[Literal[0], None] | tuple[int, UserDailyTokens]:
        try:
            # Получаем токены пользователя
            user_tokens_object: UserDailyTokens = UserDailyTokens.objects.get_or_create(user=self.request.user)[0]
            user_tokens = user_tokens_object.tokens_available
        except Exception as e:
            print(f'Ошибка получения токенов пользователя: {e}')
            user_tokens = 0
            return user_tokens, None
        return user_tokens, user_tokens_object

    def handle_norrmal_chat(self, client: OpenAI, chat: Chat, message: str) -> Response:
        history: list[dict] = self.get_history(chat)
        response = client.responses.create(
            model=self.MODEL,
            input=history + [{"role": "user", "content": message}], # type: ignore
            max_output_tokens=self.MAX_TOKENS_PER_REQUEST, # Максимальное количество токенов в ответе
            reasoning={
                "effort": "low", # Минимальные усилия по рассуждению
            },
            text={
                "verbosity": "low" # Минимальная детализация ответа
            })
        return response

    @classmethod
    def get_embedding(cls, client: OpenAI, message: str) -> List[float]:
        response = client.embeddings.create(
                            model=cls.EMBEDDING_MODEL,
                            input=message
                        )
        return response.data[0].embedding
    
    def handle_rag_chat(self, client: OpenAI, message: str):
        embedding = self.get_embedding(client, message) 
        relevant_articles = self.search_relevant(embedding)
        context = self.build_context(relevant_articles)
        prompt = self.get_prompt(context)
        response = client.responses.create(
            model=self.MODEL,
            input=[{"role": "system", "content": prompt},
                    {"role": "user", "content": message}],
            max_output_tokens=self.MAX_TOKENS_PER_REQUEST, # Максимальное количество токенов в ответе
            reasoning={
                "effort": "low", # Минимальные усилия по рассуждению
            },
            text={
                "verbosity": "low" # Минимальная детализация ответа
            })
        return response

    @staticmethod
    def append_messages_in_bd(chat: Chat, message: str, response: Response, is_rag):
        Message.objects.create(chat=chat, content=message, role="user", is_rag=is_rag)
        Message.objects.create(chat=chat, content=response.output_text, role="assistant", is_rag=is_rag)

    @classmethod
    def get_history(cls, chat: Chat) -> list[dict]:
        return [{"role": mes.role, "content": mes.content}
                for mes in chat.messages.order_by('-created_at')[:cls.COUNTS_MESSAGE_HISTORY:-1] if not mes.is_rag] # type: ignore

    @classmethod
    def search_relevant(cls, embedding):
        # Поиск ближайших соседей
        return ArticleChunk.objects.filter(embedding__isnull=False).order_by(CosineDistance('embedding', vector=embedding))[:cls.K]

    @staticmethod
    def build_context(relevant_articles) -> str:
        # Построение контекста для модели
        texts = "\n\n".join(f'{article_chunk.article.title}: {article_chunk.text}' for article_chunk in relevant_articles)
        return  f"Вот некоторые статьи из базы знаний:\n{texts}"

    @staticmethod
    def get_prompt(context: str) -> str:
        return f"""Ты - умный ассистент. Отвечай на вопросы пользователя, основываясь на приведённой информации из базы знаний.\n
                Контекст:
                {context}
                Если ответа в базе знаний нет, честно скажи: "По имеющимся статьям я не нашёл ответа, попробуйте спросить в обычном чате".
                Если ответ найден в конце приведи источники с назщваниями статей."""

    @classmethod
    def delete_old_messages(cls, chat: Chat) -> None:
        # Удаляем старые сообщения
        time_limit = cls.get_check_time_limit()
        chat.messages.filter(created_at__lt=time_limit).delete() # type: ignore

    @classmethod
    def get_check_time_limit(cls) -> datetime.datetime:
        # Возвращает дату, более раннюю чем три месяца назад
        today = datetime.datetime.now(datetime.timezone.utc)
        three_months_date = today - datetime.timedelta(days=cls.DAYS_LIMIT)
        return three_months_date

    @classmethod
    def load_encoding(cls) -> tiktoken.Encoding:
        # load an encoding by name
        try:
            encoding = tiktoken.encoding_for_model(cls.MODEL)
        except KeyError:
            encoding = tiktoken.get_encoding(cls.ENCODING_DEFAULT_NAME)
        return encoding
    
    @staticmethod
    def get_string_from_request(history: list[dict], output) -> str:
        # Объединение в строку истории сообщений и исходящего сообщений
        string = "".join((message['content'] for message in history)) + output
        return string

    @classmethod
    def num_tokens_from_string(cls, string: str) -> int:
        """Returns the number of tokens in a text string."""
        encoding = cls.load_encoding()
        num_tokens = len(encoding.encode(string))
        num_tokens += 3  # every reply is primed with <|start|>assistant<|messa
        return num_tokens

    @classmethod
    def update_everyday_user_tokens(cls, user_tokens_object: UserDailyTokens):
        if cls.next_day_arrived(user_tokens_object):
            user_tokens_object.tokens_available = cls.TOKENS_PER_DAY
            user_tokens_object.date = datetime.datetime.now(datetime.timezone.utc)
            user_tokens_object.save()

    @staticmethod
    def next_day_arrived(user_tokens_object: UserDailyTokens) -> bool:
        # Проверка наступления следующего дня
        today = datetime.datetime.now(datetime.timezone.utc)
        one_day = datetime.timedelta(days=1)
        return today - one_day >= user_tokens_object.date