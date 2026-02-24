"""
Custom renderers for TeamSync.
"""
from rest_framework.renderers import JSONRenderer


class StandardJSONRenderer(JSONRenderer):
    """
    Custom JSON renderer that wraps responses in a standard format.
    """
    def render(self, data, accepted_media_type=None, renderer_context=None):
        response = renderer_context['response'] if renderer_context else None
        
        # If data is already in standard format, don't wrap it again
        if isinstance(data, dict) and 'code' in data and 'message' in data:
            return super().render(data, accepted_media_type, renderer_context)
        
        # Wrap the data in standard format
        status_code = response.status_code if response else 200
        
        if status_code >= 400:
            # Error response
            wrapped_data = {
                'code': status_code,
                'message': data.get('detail', '请求失败') if isinstance(data, dict) else '请求失败',
                'errors': data if isinstance(data, dict) else {}
            }
        else:
            # Success response
            wrapped_data = {
                'code': status_code,
                'message': 'success',
                'data': data
            }
        
        return super().render(wrapped_data, accepted_media_type, renderer_context)
