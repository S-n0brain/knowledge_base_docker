import json
from django.http import JsonResponse
from django.views.generic import DetailView
from openai import OpenAI
from knowledge_base.settings import API_GPT_KEY
from .forms import ChatForm
from .models import Chat, Message
from django.contrib.auth.mixins import LoginRequiredMixin

class ChatView(LoginRequiredMixin, DetailView):
    BASE_URL_MODAL = "https://api.proxyapi.ru/openai/v1"
    COUNTS_MESSAGE_HISTORY = 5
    template_name = 'chatbot/chat.html'
    form_class = ChatForm
    model = Chat

    def get_context_data(self, **kwargs) -> dict:
        context = super().get_context_data(**kwargs)
        context['form'] = self.form_class()
        context['messages'] = Message.objects.filter(chat=self.get_object()).order_by('created_at')
        return context

    def get_object(self):
        user = self.request.user
        chat, created = Chat.objects.get_or_create(user=user)
        return chat

    def get_client(self) -> OpenAI:
        return OpenAI(api_key=API_GPT_KEY, base_url=self.BASE_URL_MODAL)

    def post(self, *args, **kwargs) -> JsonResponse:
        data = json.loads(self.request.body)
        message = data.get("message", "")
        if message:
            try:
                client = self.get_client()
            except Exception:
                return JsonResponse({"error": f"Ошибка получения клиента"}, status=500)
            try:
                history = [{"role": mes.role, "content": mes.content}
                           for mes in Message.objects.filter(chat=self.get_object()).order_by('-created_at')[:self.COUNTS_MESSAGE_HISTORY:-1]]
                print(f'history: {history}')
                response = client.responses.create(
                model="gpt-5-nano",
                input=history + [{"role": "user", "content": message}], # type: ignore
                max_output_tokens=250,
                reasoning={
                    "effort": "minimal",
                },
                text={
                    "verbosity": "low"
                })
            except Exception:
                return JsonResponse({"error": f"Ошибка получения ответа от модели"}, status=500)
            Message.objects.create(chat=self.get_object(),
                                             content=message, role="user")
            Message.objects.create(chat=self.get_object(),
                                             content=response.output_text, role="assistant")
            return JsonResponse({"reply": response.output_text, "role": "Ассистент", "model": response.model})
        return JsonResponse({"error": f"Ошибка сообщения"}, status=400)
