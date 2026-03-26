from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response


class StandardPagination(PageNumberPagination):
    """
    Default pagination for all API list endpoints.

    Query params:
      ?page=2          — page number (1-based)
      ?page_size=20    — override page size (capped at max_page_size)
    """
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 100

    def get_paginated_response(self, data):
        return Response({
            'pagination': {
                'count':     self.page.paginator.count,
                'page':      self.page.number,
                'page_size': self.get_page_size(self.request),
                'pages':     self.page.paginator.num_pages,
                'next':      self.get_next_link(),
                'previous':  self.get_previous_link(),
            },
            'results': data,
        })

    def get_paginated_response_schema(self, schema):
        return {
            'type': 'object',
            'properties': {
                'pagination': {
                    'type': 'object',
                    'properties': {
                        'count':     {'type': 'integer'},
                        'page':      {'type': 'integer'},
                        'page_size': {'type': 'integer'},
                        'pages':     {'type': 'integer'},
                        'next':      {'type': 'string', 'nullable': True},
                        'previous':  {'type': 'string', 'nullable': True},
                    },
                },
                'results': schema,
            },
        }