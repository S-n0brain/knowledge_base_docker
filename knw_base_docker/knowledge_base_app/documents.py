from django_elasticsearch_dsl import Document, Index, fields
from django_elasticsearch_dsl.registries import registry
from .models import Article

@registry.register_document
class ArticleDocument(Document):
    topic = fields.TextField(attr="topic.title")
    content = fields.TextField(attr='get_plain_content')

    class Index:
         name = 'articles'
         settings = {'number_of_shards': 1,
                    'number_of_replicas': 0,
                    "analysis": {
      "filter": {
          "russian_stop": {
          "type":       "stop",
          "stopwords":  "_russian_"
        },
        "russian_stemmer": {
          "type":       "stemmer",
          "language":   "russian"
        }
      },
      "analyzer": {
        "rebuilt_russian": {
          "tokenizer":  "standard",
          "filter": [
            "lowercase",
            "russian_stop",
            "russian_stemmer",
          ]
        }
      }
    }
  }

    class Django:
        model = Article
        fields = [
            'title',
        ]