from django.urls import path, include
from rest_framework.routers import Route, DynamicRoute, SimpleRouter

from .views import complete, UserViewSet, delete


class DefaultRouter(SimpleRouter):
    routes = [
        Route(
            url=r'^{prefix}$',
            mapping={'get': 'list'},
            name='{basename}-list',
            detail=False,
            initkwargs={'suffix': 'List'}
        ),
        Route(
            url=r'^{prefix}/{lookup}$',
            mapping={'get': 'retrieve'},
            name='{basename}-detail',
            detail=True,
            initkwargs={'suffix': 'Detail'}
        ),
        DynamicRoute(
            url=r'^{prefix}/{lookup}/{url_path}$',
            name='{basename}-{url_name}',
            detail=True,
            initkwargs={}
        )
    ]


router = DefaultRouter()
router.register(r'users', UserViewSet, basename='user')
urlpatterns = router.urls

urlpatterns += [
    path('complete/instagram/', complete),
    path('instagram/delete/', delete)
]
