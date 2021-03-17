class Headers:
	def __init__(self, get_response):
		self.get_response = get_response

	def __call__(self, request):
		response = self.get_response(request)
		response['report-to'] = '{ "group": "csp", "includeSubdomains": true, "max_age": 604800, "endpoints": [ { "url": "https://meta.meh.is/reporting/csp", "priority": 100, "weight": 100 } ] }'
		return response

class CSRFG:
	def __init__(self, get_response):
		self.get_response = get_response

	def __call__(self, request):
		return self.get_response(request)

	def process_template_response(self, request, response):
		response.context["csrf"] = 'bacon'

		return response
