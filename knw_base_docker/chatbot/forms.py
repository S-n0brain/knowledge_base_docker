from django import forms
from .models import Message

class ChatForm(forms.ModelForm):
    content = forms.CharField(
        widget=forms.Textarea(attrs={
            'rows': 3, 
            'class': 'form-control', 
            'placeholder': 'Введите сообщение...',
            'id': 'message-input',
            'style': 'resize: none;',
        })
    )

    class Meta:
        model = Message
        fields = ['content']