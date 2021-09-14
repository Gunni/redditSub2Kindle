import json
from django.conf import settings

class Headers:
	def __init__(self, get_response):
		self.get_response = get_response

	def __call__(self, request):
		response = self.get_response(request)

		report_to = {
			'group': 'csp',
			'includeSubdomains': True,
			'max_age': 604800,
			'endpoints': [
				{
					'url': settings.SENTRY_CONFIG['report'],
					'priority': 100,
					'weight': 100,
				}
			]
		}

		response['report-to'] = json.dumps(report_to)
		return response

class CSRFG:
	def __init__(self, get_response):
		self.get_response = get_response

	def __call__(self, request):
		return self.get_response(request)

	def process_template_response(self, request, response):
		response.context["csrf"] = 'bacon'

		return response
