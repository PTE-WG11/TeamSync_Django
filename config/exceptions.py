"""
Custom exceptions for TeamSync.
"""
from rest_framework.exceptions import APIException
from rest_framework import status


class BusinessError(APIException):
    """Base business error exception."""
    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    default_code = 'business_error'
    default_detail = '业务逻辑错误'

    def __init__(self, detail=None, code=None, status_code=None):
        if status_code:
            self.status_code = status_code
        super().__init__(detail, code)


class ValidationError(BusinessError):
    """Validation error."""
    status_code = status.HTTP_400_BAD_REQUEST
    default_code = 'validation_error'
    default_detail = '数据验证失败'


class PermissionDenied(BusinessError):
    """Permission denied error."""
    status_code = status.HTTP_403_FORBIDDEN
    default_code = 'permission_denied'
    default_detail = '权限不足'


class ResourceNotFound(BusinessError):
    """Resource not found error."""
    status_code = status.HTTP_404_NOT_FOUND
    default_code = 'resource_not_found'
    default_detail = '资源不存在'


class ResourceConflict(BusinessError):
    """Resource conflict error."""
    status_code = status.HTTP_409_CONFLICT
    default_code = 'resource_conflict'
    default_detail = '资源冲突'


# Error codes mapping
ERROR_CODES = {
    # Authentication errors (1000-1099)
    1001: ('用户名或密码错误', status.HTTP_401_UNAUTHORIZED),
    1002: ('Token已过期', status.HTTP_401_UNAUTHORIZED),
    1003: ('Token无效', status.HTTP_401_UNAUTHORIZED),
    1004: ('用户未激活', status.HTTP_403_FORBIDDEN),
    
    # Project errors (2000-2099)
    2001: ('项目不存在', status.HTTP_404_NOT_FOUND),
    2002: ('项目成员已存在', status.HTTP_409_CONFLICT),
    2003: ('项目必须至少有一个成员', status.HTTP_422_UNPROCESSABLE_ENTITY),
    2004: ('项目已归档', status.HTTP_422_UNPROCESSABLE_ENTITY),
    2005: ('项目未归档，无法删除', status.HTTP_422_UNPROCESSABLE_ENTITY),
    
    # Task errors (3000-3099)
    3001: ('任务不存在', status.HTTP_404_NOT_FOUND),
    3002: ('任务层级超过限制(最多3层)', status.HTTP_422_UNPROCESSABLE_ENTITY),
    3003: ('无权创建子任务(非负责人)', status.HTTP_403_FORBIDDEN),
    3004: ('无权查看任务详情', status.HTTP_403_FORBIDDEN),
    3005: ('存在子任务，无法删除', status.HTTP_422_UNPROCESSABLE_ENTITY),
    3006: ('任务已归档，无法修改', status.HTTP_422_UNPROCESSABLE_ENTITY),
    
    # User errors (4000-4099)
    4001: ('用户不存在', status.HTTP_404_NOT_FOUND),
    4002: ('用户已是团队成员', status.HTTP_409_CONFLICT),
    4003: ('用户未加入团队', status.HTTP_403_FORBIDDEN),
    4004: ('用户名已存在', status.HTTP_409_CONFLICT),
    4005: ('邮箱已存在', status.HTTP_409_CONFLICT),
    
    # File errors (5000-5099)
    5001: ('文件上传失败', status.HTTP_500_INTERNAL_SERVER_ERROR),
    5002: ('文件类型不支持', status.HTTP_400_BAD_REQUEST),
    5003: ('文件大小超过限制', status.HTTP_400_BAD_REQUEST),
    5004: ('文件不存在', status.HTTP_404_NOT_FOUND),
    
    # Team errors (6000-6099)
    6001: ('团队不存在', status.HTTP_404_NOT_FOUND),
    6002: ('用户已是团队管理员', status.HTTP_409_CONFLICT),
}


def get_error_response(error_code, extra_message=None):
    """Get standardized error response."""
    message, status_code = ERROR_CODES.get(error_code, ('未知错误', status.HTTP_500_INTERNAL_SERVER_ERROR))
    if extra_message:
        message = f"{message}: {extra_message}"
    
    return {
        'code': error_code,
        'message': message,
        'errors': {}
    }, status_code
